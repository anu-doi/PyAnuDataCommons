'''
Australian National University Data Commons
Copyright (C) 2013  The Australian National University

This file is part of Australian National University Data Commons.

Australian National University Data Commons is free software: you
can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Rahul Khanna <rahul.khanna@anu.edu.au>
'''

import urllib
import sys
import base64
import os
import hashlib
import configparser
import logging
import http.client
from datetime import datetime

from progress import ProgressFile


VERSION = "0.1-20131128"


class AnudcClient:

	def __init__(self):
		self.__anudc_config = AnudcServerConfig()
		self.__hostname = self.__anudc_config.get_config_hostname()
		self.__protocol = self.__anudc_config.get_config_protocol()

	def __getuseragent(self):
		return "Python/" + sys.version + " " + sys.platform

		
	
	def __add_auth_header(self, headers):
		auth_token = self.__anudc_config.get_config_token()
		username = self.__anudc_config.get_config_username()
		password = self.__anudc_config.get_config_password() 
		if auth_token != None:
			headers["X-Auth-Token"] = auth_token
		elif username != None and password != None:
			username_password = base64.encodestring("%s:%s" % (username, password)).replace('\n', '')
			headers["Authorization"] = "Basic %s" % username_password
		else:
			raise Exception
	
	
	def __create_connection(self):
		if self.__protocol == "https":
			conn = http.client.HTTPSConnection(self.__hostname)
		else:
			conn = http.client.HTTPConnection(self.__hostname)
			
		return conn
	
	
	def calc_md5(self, filepath):
		start_time = datetime.now()
		print("Calculating MD5 for file " + filepath + "...")
		block_size = 65536
		data_file = None
		try:
			data_file = ProgressFile(filepath, "rb")
			digester = hashlib.md5()
		
			data_block = data_file.read(block_size)
			while len(data_block) > 0:
				digester.update(data_block)
				data_block = data_file.read(block_size)
			
			print()
			md5 = digester.hexdigest()
			delta = datetime.now() - start_time
			time_taken_sec = delta.seconds + (delta.microseconds / 1000000)
			print("MD5: " + md5 + "     [Time taken " + "{:,.1f}".format(time_taken_sec) + " sec]")
		finally:
			if data_file != None:
				data_file.close()

		return md5
	
	
	def create_record(self, metadatafile):
		headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": self.__getuseragent()}
		
		self.__add_auth_header(headers)
		
		url = self.__anudc_config.get_config_createurl()
		print()
		print("Creating record at " + self.__hostname + url + " ...")
		urlencoded_metadata = urllib.parse.urlencode(metadatafile.read_metadata_list())

		connection = self.__create_connection()
		connection.request("POST", url, urlencoded_metadata, headers)
		
		response = connection.getresponse()
		print("Status: " + str(response.status) + ", (" + response.reason + ")")
		body = str(response.read().decode("utf-8"))
		print("Body: " + body)
		
		if response.status == 201:
			print("Created record " + body)
		else:
			raise Exception("Unable to create record")
		
		pid = body
		return pid


	def create_relations(self, pid, relations):
		print()
		if relations is not None:
			for link_type, related_pid in relations:
				headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": self.__getuseragent()}
				self.__add_auth_header(headers)
			
				url = self.__anudc_config.get_config_addlinkurl() + urllib.parse.quote(pid)
				print("Creating relation: " + link_type + " " + related_pid)
				urlencoded_link = urllib.parse.urlencode({"linkType": link_type, "itemId": related_pid})
				
				connection = self.__create_connection()
				connection.request("POST", url, urlencoded_link, headers)
				
				response = connection.getresponse()
				print("Status: " + str(response.status) + ", (" + response.reason + ")")
				body = str(response.read().decode("utf-8"))
				print("Body: " + body)
		
	
	
	def upload_files(self, pid, files_to_upload):
		file_upload_statuses = {}
		print()
		for filename, filepath in files_to_upload.items():
			print("Processing file " + filepath + ":")
			
			data_file = None
			try:
				# Check if the file exists.
				if not os.path.isfile(filepath):
					raise Exception("File " + filepath + " doesn't exist.")
				
				md = self.calc_md5(filepath)
				headers = {"Content-Type": "application/octet-stream", "Accept": "text/plain", "Content-MD5": md, "User-Agent": self.__getuseragent()}
	
				self.__add_auth_header(headers)
	
				url = self.__anudc_config.get_config_uploadfileurl() + urllib.parse.quote(pid) + "/" + "data" + "/" + urllib.parse.quote(filename)
				print("Uploading " + filepath + " to " + self.__hostname + url + "...")
				data_file = ProgressFile(filepath, "rb")
				
				connection = self.__create_connection()
				connection.request("POST", url, data_file, headers)
				response = connection.getresponse()
				print()
				print("RESPONSE: [" + str(response.status) + "] " + response.reason)
				print("***********")
				print(response.read().decode("utf-8"))
				print("***********")
				if response.status == 200:
					file_upload_statuses[filepath] = 1
					print("File uploaded successfully.")
				else:
					file_upload_statuses[filepath] = 0;
					print("ERROR while uploading file.")
				print
			except Exception as e:
				print()
				print(e)
				file_upload_statuses[filepath] = 0
			finally:
				if data_file is not None:
					data_file.close()

		return file_upload_statuses
	

class AnudcServerConfig:
	
	def __init__(self):
		__filename = "anudc.conf"
		__file = open(os.path.join(os.path.dirname(__file__), __filename))
		
		self.__metadata_section = "datacommons"
		
		self.__config = configparser.ConfigParser()
		self.__config.optionxform=str
		self.__config.readfp(__file)
		__file.close()
		
	
	def get_config_value(self, section, key):
		try:
			return self.__config.get(section, key)
		except:
			return None
		
		
	def get_config_hostname(self):
		return self.get_config_value(self.__metadata_section, "host")
	
	def get_config_createurl(self):
		return self.get_config_value(self.__metadata_section, "create_url")
	
	def get_config_uploadfileurl(self):
		return self.get_config_value(self.__metadata_section, "uploadfile_url")
	
	def get_config_addlinkurl(self):
		return self.get_config_value(self.__metadata_section, "addlink_url")
	
	def get_config_token(self):
		return self.get_config_value(self.__metadata_section, "token")

	def get_config_username(self):
		return self.get_config_value(self.__metadata_section, "username")
	
	def get_config_password(self):
		return self.get_config_value(self.__metadata_section, "password")
	
	def get_config_pid_prefix(self):
		return self.get_config_value(self.__metadata_section, "pid_prefix")
	
	def get_config_protocol(self):
		return self.get_config_value(self.__metadata_section, "proto")
	
	
class MetadataFile:

	def __init__(self, filename):
		self.__filename = filename
		
		self.__metadata_section = "metadata"
		self.__pid_section = "pid"
		self.__upload_files_section = "files"
		self.__relations_section = "relations"
		
		self.__config_parser = configparser.ConfigParser()
		self.__config_parser.optionxform = str
		
		try:
			fp = self.__open_file("r")
			self.__config_parser.readfp(fp)
		finally:
			fp.close()

		
	def read_metadata_list(self):
		metadata = self.__config_parser.items(self.__metadata_section)
		for key, value in metadata:
			logging.debug(key + ": " + value)

		return metadata
	
	
	def read_upload_files_list(self):
		try:
			files_list = self.__config_parser.items(self.__upload_files_section)
		except:
			files_list = None
		return files_list
	
	
	def read_pid(self):
		try:
			pid = self.__config_parser.get(self.__pid_section, "pid")
		except:
			pid = None
		return pid
	
	
	def write_pid(self, pid):
		if not self.__config_parser.has_section(self.__pid_section):
			self.__config_parser.add_section(self.__pid_section)
			
		self.__config_parser.set(self.__pid_section, "pid", pid)
		try:
			fp = self.__open_file("w")
			self.__config_parser.write(fp)
		finally:
			fp.close()
		
		
	def read_relations(self):
		try:
			relations = self.__config_parser.items(self.__relations_section)
		except:
			relations = None
			
		return relations
		
		
	def __open_file(self, mode):
		fp = open(self.__filename, mode)
		return fp

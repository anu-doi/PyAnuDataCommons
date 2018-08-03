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
import time
from datetime import datetime

from progress import ProgressFile


VERSION = "0.1-20140410"


class AnudcClient:
	def __init__(self):
		self.__anudc_config = AnudcServerConfig()
		self.__hostname = self.__anudc_config.get_config_hostname()
		self.__protocol = self.__anudc_config.get_config_protocol()
		if self.__protocol == "https":
			self.__conn = http.client.HTTPSConnection(self.__hostname)
		else:
			self.__conn = http.client.HTTPConnection(self.__hostname)

	def __getuseragent(self):
		return "Python/" + sys.version + " " + sys.platform

		
	
	def __add_auth_header(self, headers):
		auth_token = self.__anudc_config.get_config_token()
		username = self.__anudc_config.get_config_username()
		password = self.__anudc_config.get_config_password() 
		if auth_token != None:
			headers["X-Auth-Token"] = auth_token
		elif username != None and password != None:
			bytes_username_password = bytes(username + ":" + password, "utf-8")
			bytes_username_password = base64.b64encode(bytes_username_password)
			str_username_password = str_username_password = bytes_username_password.decode("utf-8")
			headers["Authorization"] = "Basic %s" % str_username_password
		else:
			raise Exception
	
	
	def __sizeof_fmt(self, num):
		for x in ['bytes','KB','MB','GB']:
			if num < 1024.0 and num > -1024.0:
				return "%3.1f %s" % (num, x)
			num /= 1024.0
		return "%3.1f %s" % (num, 'TB')
	
	
	def __calc_md5(self, filepath):
		block_size = 65536
		data_file = None
		try:
			data_file = ProgressFile(filepath, "rb")
			digester = hashlib.md5()
		
			data_block = data_file.read(block_size)
			while len(data_block) > 0:
				digester.update(data_block)
				data_block = data_file.read(block_size)
			
			md5 = digester.hexdigest()
		finally:
			if data_file != None:
				data_file.close()

		return md5
	
	def __wait_inter_fileupload(self):
		delay_sec = int(self.__anudc_config.get_config_inter_fileupload_delay())
		if delay_sec > 0:
			try:
				for i in range(0,delay_sec):
					if sys.stdout.isatty():
						status_str = "\rWaiting " + str(i + 1) + "/" + str(delay_sec) + "..." 
						print(status_str, end="")
						sys.stdout.flush()
					time.sleep(1)
				print()
			except KeyboardInterrupt:
				try:
					input("Press Enter key to continue...")
				except (KeyboardInterrupt):
					return
	
	
	def create_record(self, metadatafile):
		headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": self.__getuseragent()}
		
		self.__add_auth_header(headers)
		
		url = self.__anudc_config.get_config_createurl()
		print()
		print("Creating record at " + self.__hostname + url + " ...")
		urlencoded_metadata = urllib.parse.urlencode(metadatafile.read_metadata_list())

		self.__conn.request("POST", url, urlencoded_metadata, headers)
		
		response = self.__conn.getresponse()
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
				
				self.__conn.request("POST", url, urlencoded_link, headers)
				
				response = self.__conn.getresponse()
				print("Status: " + str(response.status) + ", (" + response.reason + ")")
				body = str(response.read().decode("utf-8"))
				print("Body: " + body)
		
	
	
	def upload_files(self, pid, files_to_upload):
		file_upload_statuses = {}
		print()
		cur_file_count = 0
		n_files_to_upload = len(files_to_upload.items())
		for target_path, local_filepath in files_to_upload.items():
			cur_file_count += 1
			print("Processing file (" + str(cur_file_count) + "/" + str(n_files_to_upload) + ") for " + pid + ":")
			data_file = None
			try:
				# Check if the file exists.
				if not os.path.isfile(local_filepath):
					raise Exception("File " + local_filepath + " doesn't exist.")
				
				url = self.__anudc_config.get_config_uploadfileurl() + urllib.parse.quote(pid) + "/" + "data" + urllib.parse.quote(target_path)
				
				print("\tSource File: " + local_filepath + "  (" + self.__sizeof_fmt(os.path.getsize(local_filepath)) + ")")
				print("\tTarget URL: " + self.__hostname + url)

				print("\tCalculating MD5: ", end="")
				sys.stdout.flush()
				start_time = datetime.now()
				md = self.__calc_md5(local_filepath)
				delta = datetime.now() - start_time
				time_taken_sec = delta.seconds + (delta.microseconds / 1000000)
				print("\tMD5: " + md + "     [Time taken " + "{:,.1f}".format(time_taken_sec) + " sec]")

				headers = {"Content-Type": "application/octet-stream", "Accept": "text/plain", "Content-MD5": md, "User-Agent": self.__getuseragent()}
				self.__add_auth_header(headers)
				
				retry_count = 3
				should_upload = True
				response = None
				while retry_count > 0:
					try:
						self.__conn.request("HEAD", url, None, headers)
						response = self.__conn.getresponse()
						if response.status != 404:
							if response.getheader("Content-MD5") == md:
								# Need to read whole response before sending next request
								print("\tServer contains exact copy of " + local_filepath + ": SKIPPING.")
								print()
								file_upload_statuses[local_filepath] = 1
								should_upload = False
								break
						retry_count = 0
					except:
						self.__conn.close()
						time.sleep(10)
						self.__conn.connect()
						retry_count -= 1
					finally:
						if response != None:
							response.read()
				
				if not should_upload:
					continue
				
				start_time = datetime.now()
				retry_count = 3
				while retry_count > 0:
					try:
						print("\tUploading: ", end="")
						data_file = ProgressFile(local_filepath, "rb")
						self.__conn.request("POST", url, data_file, headers)
						retry_count = 0
						response = self.__conn.getresponse()
						print("\tResponse: [" + str(response.status) + ":" + response.reason + "] " + response.read().decode("utf-8"))
						print("\tStatus: ", end="")
						if response.status == 200 or response.status == 201:
							file_upload_statuses[local_filepath] = 1
							print("SUCCESS")
						else:
							file_upload_statuses[local_filepath] = 0
							print("ERROR")
					except:
						e = sys.exc_info()[0]
						print("Retrying because of:", e)
						self.__conn.close()
						time.sleep(10)
						self.__conn.connect()
						retry_count -= 1
					finally:
						if data_file is not None:
							data_file.close()
				
				print
			except Exception as e:
				print()
				print(e)
				file_upload_statuses[local_filepath] = 0
			finally:
				if data_file is not None:
					data_file.close()
				if response is not None:
					response.read()
					
			if cur_file_count < n_files_to_upload:
				self.__wait_inter_fileupload();

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
	
	def get_config_inter_fileupload_delay(self):
		delay = self.get_config_value(self.__metadata_section, "inter_fileupload_delay")
		if delay is None:
			delay = 3
		return delay
	
class MetadataFile:

	def __init__(self, filename, delimiter="||"):
		self.__filename = filename
		
		self.__metadata_section = "metadata"
		self.__pid_section = "pid"
		self.__upload_files_section = "files"
		self.__relations_section = "relations"
		self.__delimiter = delimiter
		
		self.__config_parser = configparser.ConfigParser()
#		self.__config_parser = configparser.ConfigParser(dict_type=MultiOrderedDict,strict=False)
		self.__config_parser.optionxform = str
		
		try:
			fp = self.__open_file("r", encoding='utf-8')
			self.__config_parser.readfp(fp)
		finally:
			fp.close()

		
	def read_metadata_list(self):
		parsermetadata = self.__config_parser.items(self.__metadata_section)
		
		metadata = []
		
		for key, value in parsermetadata:
			splitvals = value.split(sep=self.__delimiter)
			for val in splitvals:
				metadata.append((key,val))
		
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
		
		
	def __open_file(self, mode, encoding='utf-8'):
		fp = open(self.__filename, mode)
		return fp

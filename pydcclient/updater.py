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

import urllib.request
import logging
import configparser
import os.path
import time

UPDATE_CHECK_THRESHOLD = 24 * 3600 * 3600
LOGGER_NAME = "Updater"
MANIFEST_FILENAME = "manifest.properties"
DISABLE_UPDATE_FILE = "DO_NOT_UPDATE"
TEMP_FILE_SUFFIX = ".tmp"

VERSION = "0.1-20131128"


class Updater:
	
	def __init__(self, manifest_url=None, base_dir = os.path.dirname(os.path.abspath(__file__)), force = False):
		self.__logger = logging.getLogger(LOGGER_NAME)
		self.__manifest_url = manifest_url
		self.__force_update = force
		self.__base_dir = base_dir
		self.__downloaded_files = []
		return

	
	def __download_file(self, url, filepath):
		os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok = True)
		urllib.request.urlretrieve(url, filename=filepath)
		self.__downloaded_files.append(filepath)
		self.__logger.debug(url + " saved as local file " + filepath)
		return

		
	def __read_manifest(self, filepath):
		manifest_file = open(filepath, mode='r')
		try:
			config = configparser.ConfigParser()
			config.read_file(manifest_file)
			manifest = Manifest()
			manifest.current_version = config.get("version", "current_version")
			filepaths = config.options("files")
			manifest.filepaths = []
			
			for filepath in filepaths:
				manifest.filepaths.append((filepath, config.get("files", filepath)))
				
		finally:
			manifest_file.close()
		
		return manifest
	
	
	def __is_manifest_updated(self, manifest_old, manifest_new):
		return int(manifest_new.current_version) > int(manifest_old.current_version)

	
	def __generate_temp_filename(self, filepath):
		return filepath + TEMP_FILE_SUFFIX
	
		
	def __strip_temp_suffix(self, filepath=""):
		if not filepath.endswith(TEMP_FILE_SUFFIX):
			raise ValueError()

		return filepath[:-4]

	
	def __delete_if_exists(self, filepath):
		if os.path.isfile(filepath):
			os.remove(filepath)
			
			
	def __prepend_base_dir(self, filepath):
		return os.path.join(self.__base_dir, filepath)
			

	def update(self):
		# Do not perform update if DO_NOT_UPDATE file exists.
		if os.path.isfile(self.__prepend_base_dir(DISABLE_UPDATE_FILE)):
			self.__logger.info("File " + DISABLE_UPDATE_FILE + " found. Skipping update")
			return
		
		manifest_old_filepath = self.__prepend_base_dir(MANIFEST_FILENAME)
		manifest_new_filepath = self.__prepend_base_dir(self.__generate_temp_filename(manifest_old_filepath))

		try:
			manifest_old = None
			if os.path.isfile(manifest_old_filepath):
				manifest_old = self.__read_manifest(manifest_old_filepath)
				
			# Check for sufficient time since the last update.
			if self.__force_update or manifest_old is None or (time.time() - os.path.getmtime(manifest_old_filepath) >= UPDATE_CHECK_THRESHOLD):
				# Download manifest
				self.__delete_if_exists(manifest_new_filepath)
				self.__download_file(self.__manifest_url, manifest_new_filepath)
				
				# Read new manifest
				manifest_new = self.__read_manifest(manifest_new_filepath)
				
				# If a previous manifest is not found or the new manifest is of a newer version, or force update flag set, proceed with update
				if manifest_old is None or self.__is_manifest_updated(manifest_old, manifest_new) or self.__force_update:
					if manifest_old is None:
						self.__logger.info("No existing manifest file found. Forcing update")
					elif self.__force_update:
						self.__logger.info("Force update flag set.")
					else:
						self.__logger.info("Downloaded manifest has newer version than old. Performing update.")
						
					# Download files in manifest and save as temp files
					i = 0
					for filepath in manifest_new.filepaths:
						self.__download_file(filepath[1], self.__prepend_base_dir(self.__generate_temp_filename(filepath[0])))
						i += 1
						self.__logger.info("Downloaded file " + str(i) + " of " + str(len(manifest_new.filepaths)) + ": " + filepath[0] + " from " + filepath[1])
					
					# Delete existing files
					i = 0
					for filepath in manifest_new.filepaths:
						self.__delete_if_exists(self.__prepend_base_dir(filepath[0]))
						i += 1
						self.__logger.info("Deleted existing file " + str(i) + " of " + str(len(manifest_new.filepaths)) + ": " + filepath[0])
					
					# Rename downloaded files to old names
					i = 0
					for filepath in manifest_new.filepaths:
						os.rename(self.__prepend_base_dir(self.__generate_temp_filename(filepath[0])), self.__prepend_base_dir(filepath[0]))
						i += 1
						self.__logger.info("Renamed file " + str(i) + " of " + str(len(manifest_new.filepaths)) + ": " + filepath[0])
						
					# Replace old manifest with new manifest
					self.__delete_if_exists(manifest_old_filepath)
					os.rename(manifest_new_filepath, manifest_old_filepath)
					
					self.__logger.info("Update complete")
				else:
					# Rename new manifest file to old manifest file
					if os.path.isfile(manifest_old_filepath):
						os.remove(manifest_new_filepath)
					else:
						os.rename(manifest_new_filepath, manifest_old_filepath)
						
					# Touch the manifest file.
					os.utime(manifest_old_filepath, None)
		finally:
			for filepath in self.__downloaded_files:
				if filepath.endswith(TEMP_FILE_SUFFIX):
					self.__delete_if_exists(filepath)
		

class Manifest:
	pass

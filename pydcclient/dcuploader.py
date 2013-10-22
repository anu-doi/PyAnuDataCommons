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

# from optparse import OptionParser
import argparse
import os.path
import logging
import sys

from pydcclient.anudclib import MetadataFile
from pydcclient.anudclib import AnudcClient
from updater.updater import Updater

VERSION = "0.1-20131022"
MANIFEST_URL = "http://localhost:8081/downloads/manifest.properties"

def init_cmd_parser():
	parser = argparse.ArgumentParser()

	parser.add_argument("-c", "--createnew", dest="metadata_file", help="File containing metadata used to create a new Collection record.")
	parser.add_argument("-p", "--pid", dest="pid", help="Identifier of an existing Collection Record on which actions are to be performed.")
	parser.add_argument("-f", "--file", dest="files", action="append", help="File(s) to upload")
	parser.add_argument("-v", "--version", action='version', version="ANU Data Uploader " + VERSION)

	args = sys.argv
	if len(args) <= 1:
		args.append("-h")

	return parser.parse_args(args)

	
def init_logging():
	logging.basicConfig(level=logging.DEBUG, format=logging.BASIC_FORMAT)


# Returns True if a file exists, False otherwise
def check_file_exists(filename):
	return os.path.isfile(filename)


def display_summary(pid, file_status):
	print
	print ("Upload Summary to", pid) 
	print ("---------------------------")
	for key, value in file_status.items():
		print(key, ": ", end="")
		if value == 1:
			print ("SUCCESS")
		else:
			print ("ERROR")


def update():
	updater = Updater(manifest_url=MANIFEST_URL, base_dir="..")
	updater.update()


def main():
	cmd_params = init_cmd_parser()
	init_logging()
	
	update()
	
	anudc = AnudcClient()
	pid = None
	files_to_upload = {}
	
	# If a metadata file has been provided as command line arg, then create the record from the data. If
	# it doesn't exist and read files to upload from it.
	if cmd_params.metadata_file != None:
		if not check_file_exists(cmd_params.metadata_file):
			raise Exception("Metadata file " + cmd_params.metadata_file + " doesn't exist.")

		metadatafile = MetadataFile(cmd_params.metadata_file)
		
		# Create record if PID doesn't already exist in the metadata file. Else, read the PID to upload files to it.
		if metadatafile.read_pid() == None:
			pid = anudc.create_record(metadatafile)
			metadatafile.write_pid(pid)
			
			# Create relations
			anudc.create_relations(pid, metadatafile.read_relations())
		else:
			pid = metadatafile.read_pid()

		# Add list of files to upload if any in the metadata file.		
		metadata_file_list = metadatafile.read_upload_files_list()
		if metadata_file_list != None:
			for name, filepath in metadata_file_list:
				files_to_upload[name] = filepath

	
	# If a new record wasn't created and the PID wasn't found in metadata file, check if it's provided as a cmd arg.
	if pid == None and cmd_params.pid != None:
		pid = cmd_params.pid

	# If still no PID, raise exception
	if pid == None:
		raise Exception("No Pid available")

	# Add list of files to upload specified as cmd args.
	if cmd_params.files != None:
		for local_file_path in cmd_params.files:
			files_to_upload[os.path.basename(local_file_path)] = local_file_path
	
	# If there are any files to upload, upload them.
	if len(files_to_upload) > 0:
		file_status = anudc.upload_files(pid, files_to_upload)
		display_summary(pid, file_status)
		
	print
	

if __name__ == '__main__':
	main()

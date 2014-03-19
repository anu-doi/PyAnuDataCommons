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

import argparse
import os.path
import logging
import sys
from urllib.error import HTTPError

from anudclib import MetadataFile
from anudclib import AnudcClient
from updater import Updater


VERSION = "0.1-20140204"
MANIFEST_URL = "https://raw.github.com/anu-doi/PyAnuDataCommons/master/pydcclient/manifest.properties"


def init_cmd_parser():
	parser = argparse.ArgumentParser()

	parser.add_argument("-c", "--createnew", dest="metadata_file", help="File containing metadata used to create a new Collection record.")
	parser.add_argument("-p", "--pid", dest="pid", help="Identifier of an existing Collection Record on which actions are to be performed.")
	parser.add_argument("-f", "--file", dest="files", action="append", help="File(s) to upload")
	parser.add_argument("-v", "--version", action='version', version="ANU Data Uploader " + VERSION)

	if len(sys.argv) <= 1:
		parser.print_help()
		sys.exit()

	return parser.parse_args()


def init_logging():
	logging.basicConfig(level=logging.DEBUG, format=logging.BASIC_FORMAT)


# Returns True if a file exists, False otherwise
def check_file_exists(filename):
	return os.path.isfile(filename)


def display_summary(pid, file_status):
	print()
	print("UPLOAD SUMMARY -", pid)
	print("---------------------------")
	i = 0
	success_count = 0;
	failed_count = 0;
	for key, value in file_status.items():
		i += 1
		if value == 1:
			status = "SUCCESS"
			success_count += 1;
		else:
			status = "ERROR"
			failed_count += 1;

		try:
			print("{}. {:>7} : {}".format(str(i), status, key))
		except:
			pass

	print("{} successful. {} failed.".format(str(success_count), str(failed_count)))


def update():
	try:
		updater = Updater(manifest_url=MANIFEST_URL, base_dir=os.path.dirname(os.path.abspath(__file__)))
		updater.update()
	except HTTPError as e:
		print("Unable to download manifest file from " + MANIFEST_URL + " - skipping update. Error: " + str(e))


def normalise_path_separators(path):
	return path.replace("\\", "/")


def list_files_in_dir(rootpath):
	'''Lists files in the specified directory and all its subdirectories. If the specified path is a file, then the specified path itself is returned.
	'''

	filepath_list = []

	if os.path.isdir(rootpath):
		# Must have topdown=True as we're modifying dirs in place to exclude those whose names start with '.'
		for root, dirs, files in os.walk(rootpath, topdown=True):
			dirs[:] = [d for d in dirs if not d[0] == '.']
			files = [f for f in files if not f[0] == '.']
			for file in files:
				filepath = os.path.join(root, file)
				filepath_list.append(normalise_path_separators(filepath))
	elif os.path.isfile(rootpath):
		filepath_list.append(normalise_path_separators(rootpath))
	else:
		print("WARNING: File or folder {} doesn't exist.".format(rootpath))

	return filepath_list


def main():
	print()
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
			for target_rel_path, uploadable in metadata_file_list:
				local_filepaths = list_files_in_dir(uploadable)
				for local_filepath in local_filepaths:
					if os.path.isfile(uploadable):
						files_to_upload[target_rel_path] = local_filepath
					elif os.path.isdir(uploadable):
						relpath = target_rel_path
						if relpath[-1:] != "/":
							relpath += "/"
						relpath += normalise_path_separators(os.path.relpath(local_filepath, os.path.dirname(uploadable)))
						files_to_upload[relpath] = local_filepath


	# If a new record wasn't created and the PID wasn't found in metadata file, check if it's provided as a cmd arg.
	if pid == None and cmd_params.pid != None:
		pid = cmd_params.pid

	# If still no PID, raise exception
	if pid == None:
		raise Exception("No Pid available")

	# Add list of files to upload specified as cmd args.
	if cmd_params.files != None:
		for file_param in cmd_params.files:
			local_filepaths = list_files_in_dir(file_param)
			for local_filepath in local_filepaths:
				if os.path.isfile(file_param):
					files_to_upload["/" + os.path.basename(local_filepath)] = local_filepath
				elif os.path.isdir(file_param):
					relpath = os.path.relpath(local_filepath, os.path.dirname(file_param))
					files_to_upload["/" + relpath.replace("\\", "/")] = local_filepath


	# If there are any files to upload, upload them.
	if len(files_to_upload) > 0:
		file_status = anudc.upload_files(pid, files_to_upload)
		display_summary(pid, file_status)

	print()


if __name__ == '__main__':
	main()

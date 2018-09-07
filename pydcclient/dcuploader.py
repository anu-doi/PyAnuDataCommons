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
import tkinter
import tkinter.filedialog
import tkinter.messagebox
from urllib.error import HTTPError

from anudclib import MetadataFile
from anudclib import AnudcClient
from updater import Updater


VERSION = "0.1-20180907"
MANIFEST_URL = "https://raw.github.com/anu-doi/PyAnuDataCommons/master/pydcclient/manifest.properties"


def init_cmd_parser():
	parser = argparse.ArgumentParser()

	parser.add_argument("-c", "--createnew", dest="metadata_file", help="File containing metadata used to create a new Collection record.")
	parser.add_argument("-p", "--pid", dest="pid", help="Identifier of an existing Collection Record on which actions are to be performed.")
	parser.add_argument("files", nargs="*", help="File(s) to upload")
	parser.add_argument("--gui", action="store_true", help="Start GUI interface")
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


def create_uploadables(server_dir, local_filepath_list):
	uploadable_list = {}
	
	# Normalise server_dir - prefix and suffix with '/'. If empty string, change to "/"
	if server_dir == "":
		server_dir = "/"
	if server_dir[0:1] != "/":
		server_dir = "/" + server_dir
	if server_dir[-1:] != "/":
		server_dir += "/"
	
	if local_filepath_list != None:
		for local_filepath in local_filepath_list:
			local_files = list_files_in_dir(local_filepath)
			for local_file in local_files:
				if os.path.isfile(local_filepath):
					uploadable_list[server_dir + os.path.basename(local_file)] = local_file
				elif os.path.isdir(local_filepath):
					server_rel_path = os.path.relpath(local_file, os.path.dirname(local_filepath))
					server_rel_path = normalise_path_separators(server_rel_path)
					uploadable_list[server_dir + server_rel_path] = local_file
	return uploadable_list


def main():
	print()
	cmd_params = init_cmd_parser()
	init_logging()

	update()

	anudc = AnudcClient()
	
	if cmd_params.gui:
		UploadWindow(anudc=anudc, cmd_params=cmd_params).mainloop()
	else:
		CommandLineManager(anudc=anudc, cmd_params=cmd_params).process()
		
		
class CommandLineManager():
	def __init__(self, anudc=None, cmd_params=None):
		self.__anudc = anudc
		self.__cmd_params = cmd_params
		
	def process(self):
		pid = None
		files_to_upload = {}
	
		# If a metadata file has been provided as command line arg, then create the record from the data. If
		# it doesn't exist and read files to upload from it.
		if self.__cmd_params.metadata_file != None:
			if not check_file_exists(self.__cmd_params.metadata_file):
				raise Exception("Metadata file " + self.__cmd_params.metadata_file + " doesn't exist.")
	
			metadatafile = MetadataFile(self.__cmd_params.metadata_file)
	
			# Create record if PID doesn't already exist in the metadata file. Else, read the PID to upload files to it.
			if metadatafile.read_pid() == None:
				pid = self.__anudc.create_record(metadatafile)
				metadatafile.write_pid(pid)
	
				# Create relations
				self.__anudc.create_relations(pid, metadatafile.read_relations())
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
		if pid == None and self.__cmd_params.pid != None:
			pid = self.__cmd_params.pid
	
		# If still no PID, raise exception
		if pid == None:
			raise Exception("No Pid available")
	
		# Add list of files to upload specified as cmd args.
		files_to_upload.update(create_uploadables("/", self.__cmd_params.files))
	# 	if cmd_params.files != None:
	# 		for file_param in cmd_params.files:
	# 			local_filepaths = list_files_in_dir(file_param)
	# 			for local_filepath in local_filepaths:
	# 				if os.path.isfile(file_param):
	# 					files_to_upload["/" + os.path.basename(local_filepath)] = local_filepath
	# 				elif os.path.isdir(file_param):
	# 					relpath = os.path.relpath(local_filepath, os.path.dirname(file_param))
	# 					files_to_upload["/" + relpath.replace("\\", "/")] = local_filepath
	
	
		# If there are any files to upload, upload them.
		if len(files_to_upload) > 0:
			file_status = self.__anudc.upload_files(pid, files_to_upload)
			display_summary(pid, file_status)
	
		print()

	
class UploadWindow(tkinter.Frame):
	def __init__(self, master=None, anudc=None, cmd_params=None):
		self.__anudc = anudc
		self.__local_filepaths = set()
		self.__cmd_params = cmd_params
		
		tkinter.Frame.__init__(self, master, width=500, height=500)
		self.grid(sticky="WE")
		self.master.title("ANU Data Commons")
		
		label_pid = tkinter.Label(self, text="Identifier: ", underline=0)
		label_pid.grid(row=0, column=0, columnspan=1, sticky=tkinter.W)

		self.__entry_pid = tkinter.Entry(self, width=30)
		self.__entry_pid.focus()
		self.__entry_pid.grid(row=0, column=1, columnspan=1)
		self.__set_pid_initial_value()
		
		label_dir_on_server = tkinter.Label(self, text="Server Directory: ", underline=0)
		label_dir_on_server.grid(row=1, column=0, sticky=tkinter.W)
		
		self.__entry_server_dir = tkinter.Entry(self, width=30)
		self.__entry_server_dir.grid(row=1, column=1)

		label_upload_item = tkinter.Label(self, text="Upload:")
		label_upload_item.grid(row=2, column=0, columnspan=1, sticky=tkinter.W)

		button_add_files = tkinter.Button(self, text="Add Files...", command=self.__button_add_files_click)
		button_add_files.grid(row=2, column=1, columnspan=1)

		button_add_dir = tkinter.Button(self, text="Add Folder...", command=self.__button_add_folder_click)
		button_add_dir.grid(row=2, column=2, columnspan=1)

		self.__lb_uploadables = tkinter.Listbox(self, activestyle="none")
		self.__lb_uploadables.grid(row=3, column=0, columnspan=3, sticky="WE")
		
		button_upload = tkinter.Button(self, text="Upload to Data Commons", underline=0, command=self.__button_upload_click)
		button_upload.grid(row=4, column=1, columnspan=1)
		
		button_reset = tkinter.Button(self, text="Reset", command=self.__button_reset_click)
		button_reset.grid(row=4, column=2, columnspan=1)
		
		self.pack(fill=tkinter.BOTH, expand=tkinter.YES)


	def __button_add_files_click(self):
		filepaths = tkinter.filedialog.askopenfilename(multiple=True)
		if type(filepaths) != "str" and filepaths != "":
			# filepaths is a tuple. Converting it into a list of strings
			self.__local_filepaths.update(list(filepaths))
			self.__refresh_lb_uploadables()

	def __button_add_folder_click(self):
		folder = tkinter.filedialog.askdirectory(mustexist=True)
		if folder != "":
			# folder is a string. Wrapping it in a list
			self.__local_filepaths.add(folder)
			self.__refresh_lb_uploadables()

	def __button_upload_click(self):
		if len(self.__local_filepaths) > 0:
			uploadables = create_uploadables(self.__entry_server_dir.get(), self.__local_filepaths)
			file_status = self.__anudc.upload_files(self.__entry_pid.get(), uploadables)
			display_summary(self.__entry_pid.get(), file_status)
			self.__button_reset_click()
		else:
			tkinter.messagebox.showerror("No files selected", "You must select some files/folders to upload first.")

	def __button_reset_click(self):
		self.__local_filepaths.clear()
		self.__refresh_lb_uploadables()

	def __refresh_lb_uploadables(self):
		self.__lb_uploadables.delete(0, tkinter.END)
		for local_filepath in self.__local_filepaths:
			self.__lb_uploadables.insert(tkinter.END, local_filepath)
			
	def __set_pid_initial_value(self):
		if self.__cmd_params is not None:
			if self.__cmd_params.pid is not None:
				self.__entry_pid.insert(0, self.__cmd_params.pid)


if __name__ == "__main__":
	main()

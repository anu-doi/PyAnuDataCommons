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

import unittest
import logging
from updater import updater
import os.path

LOGGER_NAME = "UpdaterTest"

class UpdaterTest(unittest.TestCase):


	def setUp(self):
		logging.basicConfig(level=logging.DEBUG, format=logging.BASIC_FORMAT)
		self.__logger = logging.getLogger(LOGGER_NAME)


	def tearDown(self):
		pass


	def test_download_file(self):
		u = updater.Updater()
		u.download_file("http://www.anu.edu.au/mac/images/uploads/anu_agenda_19Jan.doc", "file.doc")
		self.assertTrue(os.path.isfile("file.doc"))
		self.__delete_file("file.doc")
		
		
	def test_read_manifest(self):
		u = updater.Updater()
		manifest = u.read_manifest("sample_manifest.properties")
		self.assertIsNotNone(manifest.current_version)
		print("Version:", manifest.current_version)
		for filepath in manifest.filepaths:
			print("Filepath:", filepath)

			
	def test_compare_manifests(self):
		u = updater.Updater()
		manifest_old = u.read_manifest("sample_manifest.properties")
		manifest_new = u.read_manifest("sample_manifest_dl.properties")
		self.assertTrue(u.is_manifest_updated(manifest_old, manifest_new))
		
	
	def test_temp_filenames(self):
		u = updater.Updater()
		self.assertEqual(u.generate_temp_filename("a.txt"), "a.txt.tmp")
		self.assertEqual(u.strip_temp_suffix("a.txt.tmp"), "a.txt")
		
	
	def test_full_workflow(self):
		u = updater.Updater(manifest_url="http://localhost:8081/downloads/manifest.properties", force=True)
		u.update()
		
		
	def __delete_file(self, filepath):
		if os.path.isfile(filepath):
			os.remove(filepath)



if __name__ == "__main__":
	#import sys;sys.argv = ['', 'Test.testName']
	unittest.main()
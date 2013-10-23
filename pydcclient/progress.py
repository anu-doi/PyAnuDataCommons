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

from datetime import datetime
import os


VERSION = "0.1-20131022"


class ProgressFile:
	def __init__(self, filename, mode):
		self.__f = open(filename, mode)
		self._total = os.fstat(self.__f.fileno()).st_size
		self.__f.seek(0)
		self.__percent_complete = 0
		self.__t0 = None
		
	def read(self, size):
		if self.__t0 is None:
			self.__t0 = datetime.now()
		data = self.__f.read(size)
		try:
			temp = int(self.tell() * 100 / self._total)
			if temp != self.__percent_complete:
				self.__percent_complete = temp
				ti = datetime.now()
				denom = (ti - self.__t0).seconds + ((ti - self.__t0).microseconds / 1000000)
				cur_kbps = 0
				if denom > 0:
					cur_kbps = (self.tell() / 1024) / ((ti - self.__t0).seconds + ((ti - self.__t0).microseconds / 1000000))
				print("\r{}%  [{:,.1f} KB/s]{}{}".format(str(self.__percent_complete), cur_kbps, " " * 10, "\b" * 10), end="")
		except Exception as e:
			print()
			print(e)
			pass
			
		return data

	def fileno(self):
		return self.__f.fileno()

	def tell(self):
		return self.__f.tell() 
				
	def close(self):
		self.__f.close()
		
	def __exit__(self):
		self.__f.close()
		
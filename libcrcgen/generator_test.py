# vim: ts=8 sw=8 noexpandtab
#
#   CRC code generator
#
#   Copyright (c) 2020-2022 Michael Buesch <m@bues.ch>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from libcrcgen.generator import *
from libcrcgen.reference import *
from libcrcgen.util import *

__all__ = [
	"CrcGenTest",
]

class CrcGenTest(CrcGen):
	def runTests(self, name=None, extra=None):
		tmpdir = None
		try:
			import random
			rng = random.Random()
			rng.seed(424242)

			print(f"Testing{(' ' + name) if name else ''} "
			      f"P=0x{self._P:X}, "
			      f"nrCrcBits={self._nrCrcBits}, "
			      f"shiftRight={int(bool(self._shiftRight))}, "
			      f"nrDataBits={self._nrDataBits}"
			      f"{(', ' + extra) if extra else ''} ...")

			# Generate the CRC function as Python code.
			pyCode = self.genPython(funcName="crc_pyimpl")
			execEnv = {}
			exec(pyCode, execEnv)
			crc_pyimpl = execEnv["crc_pyimpl"]

			# Generate the CRC function as C code.
			import os, time, importlib, shutil
			from cffi import FFI
			ffibuilder = FFI()
			ffibuilder.set_source("testmod_crcgen", self.genC())
			ffibuilder.cdef(self.genC(declOnly=True,
						  includeGuards=False,
						  includes=False))
			tmpdir = f"tmp_{os.getpid()}_{int(time.time() * 1e6)}"
			ffibuilder.compile(tmpdir=tmpdir, verbose=False)
			testmod_crcgen = importlib.import_module(tmpdir + ".testmod_crcgen")
			crc_cimpl = testmod_crcgen.lib.crc

			# Compare the reference implementation to the Python and C code.
			crcMask = (1 << self._nrCrcBits) - 1
			dataMask = (1 << self._nrDataBits) - 1
			for i in range(32):
				if i == 0:
					crc = 0
				elif i == 1:
					crc = crcMask
				else:
					crc = rng.randint(1, crcMask - 1)
				for j in range(min(64, dataMask + 1)):
					if j == 0:
						data = 0
					elif j == 1:
						data = dataMask
					else:
						data = rng.randint(1, dataMask - 1)
					for k in range(3):
						ref = CrcReference.crc(
							crc=crc,
							data=data,
							polynomial=self._P,
							nrCrcBits=self._nrCrcBits,
							nrDataBits=self._nrDataBits,
							shiftRight=self._shiftRight)
						py = crc_pyimpl(crc, data)
						c = crc_cimpl(crc, data)
						if ref != py or ref != c:
							raise CrcGenError(
								f"Test failed: "
								f"P=0x{self._P:X}, "
								f"nrCrcBits={self._nrCrcBits}, "
								f"shiftRight={int(bool(self._shiftRight))}, "
								f"nrDataBits={self._nrDataBits}, "
								f"data=0x{data:X}, "
								f"ref=0x{ref:X}, "
								f"py=0x{py:X}, "
								f"c=0x{c:X}")
						crc = ref
						data = (data + 1) & dataMask
		finally:
			if tmpdir:
				shutil.rmtree(tmpdir, ignore_errors=True)

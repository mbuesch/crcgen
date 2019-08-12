# vim: ts=8 sw=8 noexpandtab
#
#   CRC code generator
#
#   Copyright (c) 2019 Michael Buesch <m@bues.ch>
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

from crcgen.util import *
from crcgen.reference import *
from dataclasses import dataclass
import re

__all__ = [
	"CrcGen",
	"CrcGenError",
	"int2poly",
	"poly2int",
]

@dataclass
class AbstractBit(object):
	def flatten(self):
		return self

	def optimize(self, sortLex):
		pass

@dataclass
class Bit(AbstractBit):
	name: str
	index: int

	def gen_python(self):
		return "%s[%d]" % (self.name, self.index)

	def gen_c(self):
		return "b(%s, %d)" % (self.name, self.index)

	def gen_verilog(self):
		return "%s[%d]" % (self.name, self.index)

	def sortKey(self):
		return "%s_%07d" % (self.name, self.index)

@dataclass
class ConstBit(AbstractBit):
	value: int

	def gen_python(self):
		return "1" if self.value else "0"

	def gen_c(self):
		return "1u" if self.value else "0u"

	def gen_verilog(self):
		return "1'b1" if self.value else "1'b0"

	def sortKey(self):
		return "1" if self.value else "0"

class XOR(object):
	def __init__(self, *items):
		self.items = items

	def flatten(self):
		newItems = []
		for item in self.items:
			if isinstance(item, XOR):
				newItems.extend(item.flatten().items)
			else:
				newItems.append(item)
		self.items = newItems
		return self

	def optimize(self, sortLex):
		newItems = []
		for item in self.items:
			if isinstance(item, ConstBit):
				if item.value == 0:
					# Constant 0 does not change the XOR result.
					# Remove it.
					pass
				else:
					# Keep it.
					newItems.append(item)
			elif isinstance(item, Bit):
				if item in newItems:
					# We already have this bit.
					# Remove it.
					pass
				else:
					if sum(1 if (isinstance(i, Bit) and i == item) else 0
					       for i in self.items) % 2:
						# We have an uneven count of this bit.
						# Keep it once.
						newItems.append(item)
					else:
						# An even amount cancels out in XOR.
						# Remove it.
						pass
			else:
				# This is something else.
				# Keep it.
				newItems.append(item)
		if sortLex:
			# XOR can be arranged in any order.
			newItems.sort(key=lambda item: item.sortKey())
		if not newItems:
			# All items have been optimized out.
			# This term shall be zero.
			newItems.append(ConstBit(0))
		self.items = newItems

	def gen_python(self):
		assert(self.items)
		return "(%s)" % (" ^ ".join(item.gen_python() for item in self.items))

	def gen_c(self):
		assert(self.items)
		return "(%s)" % (" ^ ".join(item.gen_c() for item in self.items))

	def gen_verilog(self):
		assert(self.items)
		return "(%s)" % (" ^ ".join(item.gen_verilog() for item in self.items))

class Word(object):
	def __init__(self, *items, MSBFirst=True):
		if MSBFirst:
			# Reverse items, so that it's always LSB-first.
			items = reversed(items)
		self.items = list(items)

	def __getitem__(self, index):
		return self.items[index]

	def flatten(self):
		self.items = [ item.flatten() for item in self.items ]

	def optimize(self, sortLex):
		for item in self.items:
			item.optimize(sortLex)

class CrcGenError(Exception):
	pass

class CrcGen(object):
	"""Combinatorial CRC algorithm generator.
	"""

	OPT_FLATTEN	= 1 << 0 # Flatten the bit operation tree
	OPT_ELIMINATE	= 1 << 1 # Eliminate redundant operations
	OPT_LEX		= 1 << 2 # Sort the operands in lexicographical order where possible

	OPT_NONE	= 0
	OPT_ALL		= OPT_FLATTEN | OPT_ELIMINATE | OPT_LEX

	def __init__(self,
		     P,
		     nrBits,
		     shiftRight=False,
		     optimize=OPT_ALL):
		self.__P = P
		self.__nrBits = nrBits
		self.__shiftRight = shiftRight
		self.__optimize = optimize

	def __gen(self, dataVarName, crcVarName):
		nrBits = self.__nrBits
		if not 8 <= nrBits <= 64:
			raise CrcGenError("Invalid number of bits.")

		# Construct the function input data word.
		inData = Word(*(
			Bit(dataVarName, i)
			for i in reversed(range(8))
		))

		# Construct the function input CRC word.
		inCrc  = Word(*(
			Bit(crcVarName, i)
			for i in reversed(range(nrBits))
		))

		# Construct the base word.
		# This is the start word for the bit shifting loop below.
		if self.__shiftRight:
			base = Word(*(
				XOR(inData[i], inCrc[i]) if i <= 7 else ConstBit(0)
				for i in reversed(range(nrBits))
			))
		else:
			base = Word(*(
				XOR(inData[i - (nrBits - 8)] if i >= nrBits - 8 else ConstBit(0),
				    inCrc[i])
				for i in reversed(range(nrBits))
			))

		# Helper function to XOR a polynomial bit with the data bit 'dataBit',
		# if the decision bit 'queryBit' is set.
		# This is done reversed, because the polynomial is constant.
		def xor_P(dataBit, queryBit, bitNr):
			if (self.__P >> bitNr) & 1:
				return XOR(dataBit, queryBit)
			return dataBit

		# Run the main shift loop.
		prevWord = base
		for _ in range(8):
			if self.__shiftRight:
				# Shift to the right: i + 1
				word = Word(*(
					xor_P(prevWord[i + 1] if i < nrBits - 1 else ConstBit(0),
					      prevWord[0],
					      i)
					for i in reversed(range(nrBits))
				))
			else:
				# Shift to the left: i - 1
				word = Word(*(
					xor_P(prevWord[i - 1] if i > 0 else ConstBit(0),
					      prevWord[nrBits - 1],
					      i)
					for i in reversed(range(nrBits))
				))
			prevWord = word

		# Construct the function output CRC word.
		if self.__shiftRight:
			outCrc = Word(*(
				XOR(inCrc[i + 8] if i < nrBits - 8 else ConstBit(0),
				    word[i])
				for i in reversed(range(nrBits))
			))
		else:
			outCrc = word

		# Optimize the algorithm. This removes unnecessary operations.
		if self.__optimize & self.OPT_FLATTEN:
			outCrc.flatten()
		if self.__optimize & self.OPT_ELIMINATE:
			outCrc.optimize(sortLex=bool(self.__optimize & self.OPT_LEX))

		return outCrc

	def __header(self):
		return """\
THIS IS GENERATED CODE.

This code is Public Domain.
Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE
USE OR PERFORMANCE OF THIS SOFTWARE."""

	def __algDescription(self):
		return ("CRC polynomial coefficients: %s\n"
			"                             0x%X (hex)\n"
			"CRC width:                   %d bits\n"
			"CRC shift direction:         %s\n" % (
			int2poly(self.__P, self.__nrBits, self.__shiftRight),
			self.__P,
			self.__nrBits,
			"right" if self.__shiftRight else "left",
		))

	def genPython(self,
		      funcName="crc",
		      crcVarName="crc",
		      dataVarName="data"):
		word = self.__gen(dataVarName, crcVarName)
		ret = []
		ret.append("# vim: ts=8 sw=8 noexpandtab")
		ret.append("")
		ret.extend("# " + l for l in self.__header().splitlines())
		ret.append("")
		ret.extend("# " + l for l in self.__algDescription().splitlines())
		ret.append("")
		ret.append("def %s(%s, %s):" % (funcName, crcVarName, dataVarName))
		ret.append("\tclass bitwrapper:")
		ret.append("\t\tdef __init__(self, value):")
		ret.append("\t\t\tself.value = value")
		ret.append("\t\tdef __getitem__(self, index):")
		ret.append("\t\t\treturn ((self.value >> index) & 1)")
		ret.append("\t\tdef __setitem__(self, index, value):")
		ret.append("\t\t\tif value:")
		ret.append("\t\t\t\tself.value |= 1 << index")
		ret.append("\t\t\telse:")
		ret.append("\t\t\t\tself.value &= ~(1 << index)")
		ret.append("\t%s = bitwrapper(%s)" % (crcVarName, crcVarName))
		ret.append("\t%s = bitwrapper(%s)" % (dataVarName, dataVarName))
		ret.append("\tret = bitwrapper(0)")
		for i, bit in enumerate(word):
			ret.append("\tret[%d] = %s" % (i, bit.gen_python()))
		ret.append("\treturn ret.value")
		return "\n".join(ret)

	def genVerilog(self,
		       genFunction=True,
		       name="crc",
		       inDataName="inData",
		       inCrcName="inCrc",
		       outCrcName="outCrc"):
		word = self.__gen(inDataName, inCrcName)
		ret = []
		ret.append("// vim: ts=4 sw=4 noexpandtab")
		ret.append("")
		ret.extend("// " + l for l in self.__header().splitlines())
		ret.append("")
		if not genFunction:
			ret.append("`ifndef %s_V_" % name.upper())
			ret.append("`define %s_V_" % name.upper())
			ret.append("")
		ret.extend("// " + l for l in self.__algDescription().splitlines())
		ret.append("")
		if genFunction:
			ret.append("function automatic [%d:0] %s;" % (self.__nrBits - 1, name))
		else:
			ret.append("module %s (" % name)
		ret.append("\tinput [%d:0] %s%s" % (self.__nrBits - 1, inCrcName,
						    ";" if genFunction else ","))
		ret.append("\tinput [7:0] %s%s" % (inDataName,
						   ";" if genFunction else ","))
		if genFunction:
			ret.append("begin")
		else:
			ret.append("\toutput [%d:0] %s," % (self.__nrBits - 1, outCrcName))
			ret.append(");")
		for i, bit in enumerate(word):
			ret.append("\t%s%s[%d] = %s;" % ("" if genFunction else "assign ",
							 name if genFunction else outCrcName,
							 i, bit.gen_verilog()))
		if genFunction:
			ret.append("end")
			ret.append("endfunction")
		else:
			ret.append("endmodule")
			ret.append("")
			ret.append("`endif // %s_V_" % name.upper())
		return "\n".join(ret)

	def genC(self,
		 funcName="crc",
		 crcVarName="crc",
		 dataVarName="data",
		 static=False,
		 inline=False,
		 declOnly=False,
		 includeGuards=True,
		 includes=True):
		word = self.__gen(dataVarName, crcVarName)
		if self.__nrBits <= 8:
			cTypeBits = 8
		elif self.__nrBits <= 16:
			cTypeBits = 16
		elif self.__nrBits <= 32:
			cTypeBits = 32
		else:
			cTypeBits = 64
		cType = "uint%s_t" % cTypeBits
		ret = []
		ret.append("// vim: ts=4 sw=4 noexpandtab")
		ret.append("")
		ret.extend("// " + l for l in self.__header().splitlines())
		ret.append("")
		if includeGuards:
			ret.append("#ifndef %s_H_" % funcName.upper())
			ret.append("#define %s_H_" % funcName.upper())
		if includes:
			ret.append("")
			ret.append("#include <stdint.h>")
		ret.append("")
		ret.extend("// " + l for l in self.__algDescription().splitlines())
		ret.append("")
		if not declOnly:
			ret.append("#ifdef b")
			ret.append("# undef b")
			ret.append("#endif")
			ret.append("#define b(x, b) (((x) >> (b)) & 1u)")
			ret.append("")
		ret.append("{extern}{static}{inline}{cType} "
			   "{func}({cType} {crcVar}, uint8_t {dataVar}){end}".format(
			   extern="extern " if declOnly else "",
			   static="static " if static and not declOnly else "",
			   inline="inline " if inline and not declOnly else "",
			   cType=cType,
			   func=funcName,
			   crcVar=crcVarName,
			   dataVar=dataVarName,
			   end=";" if declOnly else "",
		))
		if not declOnly:
			ret.append("{")
			ret.append("\t%s ret;" % cType)
			for i, bit in enumerate(word):
				if i:
					operator = "|="
				else:
					operator = " ="
				ret.append("\tret %s (%s)%s << %d;" % (operator, cType, bit.gen_c(), i))
			ret.append("\treturn ret;")
			ret.append("}")
			ret.append("#undef b")
		if includeGuards:
			ret.append("")
			ret.append("#endif /* %s_H_ */" % funcName.upper())
		return "\n".join(ret)

	def runTests(self, name=None, extra=None):
		tmpdir = None
		try:
			import random
			rng = random.Random()
			rng.seed(424242)

			print("Testing%s P=0x%X, nrBits=%d, shiftRight=%d %s..." % (
			      (" " + name) if name else "",
			      self.__P,
			      self.__nrBits,
			      int(bool(self.__shiftRight)),
			      (extra + " ") if extra else ""))

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
			tmpdir = "tmp_%d_%d" % (os.getpid(), int(time.time() * 1e6))
			ffibuilder.compile(tmpdir=tmpdir, verbose=False)
			testmod_crcgen = importlib.import_module(tmpdir + ".testmod_crcgen")
			crc_cimpl = testmod_crcgen.lib.crc

			# Compare the reference implementation to the Python and C code.
			mask = (1 << self.__nrBits) - 1
			for i in range(0xFF + 1):
				if i == 0:
					crc = 0
				elif i == 1:
					crc = mask
				else:
					crc = rng.randint(1, mask - 1)
				for data in range(0xFF + 1):
					ref = CrcReference.crc(
						crc=crc,
						data=data,
						polynomial=self.__P,
						nrBits=self.__nrBits,
						shiftRight=self.__shiftRight)
					py = crc_pyimpl(crc, data)
					c = crc_cimpl(crc, data)
					if ref != py or ref != c:
						raise CrcGenError("Test failed. "
							"(P=0x%X, nrBits=%d, shiftRight=%d, "
							"ref=0x%X, py=0x%X, c=0x%X)" % (
							self.__P, self.__nrBits,
							int(bool(self.__shiftRight)),
							ref, py, c))
		finally:
			if tmpdir:
				shutil.rmtree(tmpdir, ignore_errors=True)

def poly2int(polyString, nrBits, shiftRight=False):
	"""Convert polynomial coefficient string to binary integer.
	"""
	polyString, _ = re.subn(r"\s+", "", polyString)
	poly = 0
	try:
		for bit in polyString.split("+"):
			bit = bit.lower()
			if bit.startswith("x^"):
				poly |= 1 << int(bit[2:])
			elif bit == "x":
				poly |= 1 << 1
			else:
				poly |= int(bit)
	except ValueError:
		raise ValueError("Invalid polynomial coefficient format.")
	poly &= (1 << nrBits) - 1
	if shiftRight:
		poly = bitreverse(poly, nrBits)
	return poly

def int2poly(poly, nrBits, shiftRight=False):
	"""Convert binary integer polynomial coefficient to string.
	"""
	poly &= (1 << nrBits) - 1
	if shiftRight:
		poly = bitreverse(poly, nrBits)
	p = []
	shift = 0
	while poly:
		if poly & 1:
			if shift == 0:
				p.append("1")
			elif shift == 1:
				p.append("x")
			else:
				p.append("x^%d" % shift)
		shift += 1
		poly >>= 1
	p.append("x^%d" % nrBits)
	return " + ".join(reversed(p))

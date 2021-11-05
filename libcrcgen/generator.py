# vim: ts=8 sw=8 noexpandtab
#
#   CRC code generator
#
#   Copyright (c) 2020-2021 Michael Buesch <m@bues.ch>
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

from dataclasses import dataclass
from libcrcgen.reference import *
from libcrcgen.util import *
import re

__all__ = [
	"CrcGen",
	"CrcGenError",
	"int2poly",
	"poly2int",
]

@dataclass(frozen=True)
class AbstractBit(object):
	def flatten(self):
		return [self, ]

	def optimize(self, sortLex):
		pass

@dataclass(frozen=True)
class Bit(AbstractBit):
	name: str
	index: int

	def gen_python(self):
		return f"{self.name}[{self.index}]"

	def gen_c(self):
		return f"b({self.name}, {self.index})"

	def gen_verilog(self):
		return f"{self.name}[{self.index}]"

	def gen_vhdl(self):
		return f"{self.name}({self.index})"

	def gen_myhdl(self):
		return f"{self.name}[{self.index}]"

	def sortKey(self):
		return f"{self.name}_{self.index:07}"

@dataclass(frozen=True)
class ConstBit(AbstractBit):
	value: int

	def gen_python(self):
		return "1" if self.value else "0"

	def gen_c(self):
		return "1u" if self.value else "0u"

	def gen_verilog(self):
		return "1'b1" if self.value else "1'b0"

	def gen_vhdl(self):
		return 'b"1"' if self.value else 'b"0"'

	def gen_myhdl(self):
		return "1" if self.value else "0"

	def sortKey(self):
		return "1" if self.value else "0"

class XOR(object):
	def __init__(self, *items):
		self.items = items

	def flatten(self):
		newItems = [ item
			     for subItem in self.items
			     for item in subItem.flatten() ]
		self.items = newItems
		return newItems

	def optimize(self, sortLex):
		newItems = []
		haveBits = {}
		constOnes = []
		for item in self.items:
			if isinstance(item, Bit):
				# Store bit for even/uneven count analysis.
				haveBits[item] = haveBits.get(item, 0) + 1
			elif isinstance(item, ConstBit):
				# Constant 0 does not change the XOR result. Remove it.
				if item.value:
					constOnes.append(item)
			else:
				# This is something else. Keep it.
				newItems.append(item)
		# An even count of the same bit is equal to zero. Remove them.
		# An uneven count of the same bit is equal to one of them. Keep one.
		newItems.extend(bit for bit, count in haveBits.items()
				if count % 2)
		# If there's an uneven amount of constant ones, keep one of them.
		if len(constOnes) % 2:
			newItems.append(constOnes[0])
		if sortLex:
			# XOR can be arranged in any order.
			newItems.sort(key=lambda item: item.sortKey())
		if not newItems:
			# All items have been optimized out.
			# This term shall be zero.
			newItems.append(ConstBit(0))
		self.items = newItems

	def gen_python(self):
		return self.__gen("(", ")", " ^ ", lambda item: item.gen_python())

	def gen_c(self):
		return self.__gen("(", ")", " ^ ", lambda item: item.gen_c())

	def gen_verilog(self):
		return self.__gen("(", ")", " ^ ", lambda item: item.gen_verilog())

	def gen_vhdl(self):
		return self.__gen("(", ")", " xor ", lambda item: item.gen_vhdl())

	def gen_myhdl(self):
		return self.__gen("(", ")", " ^ ", lambda item: item.gen_myhdl())

	def __gen(self, prefix, suffix, oper, itemGen):
		assert(self.items)
		return prefix + (oper.join(itemGen(item) for item in self.items)) + suffix

	def sortKey(self):
		return "__".join(item.sortKey() for item in self.items)

class Word(object):
	def __init__(self, *items):
		# items must be LSB first.
		self.items = list(items)

	def __getitem__(self, index):
		return self.items[index]

	def flatten(self):
		for item in self.items:
			item.flatten()

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
		     nrCrcBits,
		     nrDataBits=8,
		     shiftRight=False,
		     optimize=OPT_ALL):
		self.__P = P
		self.__nrCrcBits = nrCrcBits
		self.__nrDataBits = nrDataBits
		self.__shiftRight = shiftRight
		self.__optimize = optimize

	def __gen(self, dataVarName, crcVarName):
		nrCrcBits = self.__nrCrcBits
		nrDataBits = self.__nrDataBits
		if nrCrcBits < 1 or nrDataBits < 1:
			raise CrcGenError("Invalid number of bits.")

		# Construct the function input data word.
		inData = Word(*(
			Bit(dataVarName, i)
			for i in range(nrDataBits)
		))

		# Construct the function input CRC word.
		inCrc  = Word(*(
			Bit(crcVarName, i)
			for i in range(nrCrcBits)
		))

		# Helper function to XOR a polynomial bit with the data bit 'dataBit',
		# if the decision bit 'queryBit' is set.
		# This is done reversed, because the polynomial is constant.
		def xor_P(dataBit, queryBit, bitNr):
			if (self.__P >> bitNr) & 1:
				return XOR(dataBit, queryBit)
			return dataBit

		# Helper function to optimize the algorithm.
		# This removes unnecessary operations.
		def optimize(word, sort=False):
			if self.__optimize & self.OPT_FLATTEN:
				word.flatten()
			if self.__optimize & self.OPT_ELIMINATE:
				word.optimize(sortLex=(sort and (self.__optimize & self.OPT_LEX)))
			return word

		# Run the shift register for each input data bit.
		word = inCrc
		if self.__shiftRight:
			for i in range(nrDataBits):
				# Run the shift register once.
				bits = []
				for j in range(nrCrcBits):
					# Shift to the right: j + 1
					stateBit = word[j + 1] if j < nrCrcBits - 1 else ConstBit(0)
					# XOR the input bit with LSB.
					queryBit = XOR(word[0], inData[i])
					# XOR the polynomial coefficient, if the query bit is set.
					stateBit = xor_P(stateBit, queryBit, j)
					bits.append(stateBit)
				word = optimize(Word(*bits))
		else:
			for i in reversed(range(nrDataBits)):
				# Run the shift register once.
				bits = []
				for j in range(nrCrcBits):
					# Shift to the left: j - 1
					stateBit = word[j - 1] if j > 0 else ConstBit(0)
					# XOR the input bit with MSB.
					queryBit = XOR(word[nrCrcBits - 1], inData[i])
					# XOR the polynomial coefficient, if the query bit is set.
					stateBit = xor_P(stateBit, queryBit, j)
					bits.append(stateBit)
				word = optimize(Word(*bits))
		word = optimize(word, sort=True)

		return word

	def __header(self, language):
		return f"""\
THIS IS GENERATED {language.upper()} CODE.
https://bues.ch/h/crcgen

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
		pstr = int2poly(self.__P, self.__nrCrcBits, self.__shiftRight)
		shift = "right (little endian)" if self.__shiftRight else "left (big endian)"
		return (f"CRC polynomial coefficients: {pstr}\n"
			f"                             0x{self.__P:X} (hex)\n"
			f"CRC width:                   {self.__nrCrcBits} bits\n"
			f"CRC shift direction:         {shift}\n"
			f"Input word width:            {self.__nrDataBits} bits\n")

	def genPython(self,
		      funcName="crc",
		      crcVarName="crc",
		      dataVarName="data"):
		word = self.__gen(dataVarName, crcVarName)
		ret = []
		ret.append("# vim: ts=4 sw=4 expandtab")
		ret.append("")
		ret.extend("# " + l for l in self.__header("Python").splitlines())
		ret.append("")
		ret.extend("# " + l for l in self.__algDescription().splitlines())
		ret.append("")
		ret.append(f"def {funcName}({crcVarName}, {dataVarName}):")
		ret.append(f"    class bitwrapper:")
		ret.append(f"        def __init__(self, x):")
		ret.append(f"            self.x = x")
		ret.append(f"        def __getitem__(self, i):")
		ret.append(f"            return ((self.x >> i) & 1)")
		ret.append(f"        def __setitem__(self, i, x):")
		ret.append(f"            self.x = (self.x | (1 << i)) if x else (self.x & ~(1 << i))")
		ret.append(f"    {crcVarName} = bitwrapper({crcVarName})")
		ret.append(f"    {dataVarName} = bitwrapper({dataVarName})")
		ret.append(f"    ret = bitwrapper(0)")
		for i, bit in enumerate(word):
			ret.append(f"    ret[{i}] = {bit.gen_python()}")
		ret.append("    return ret.x")
		return "\n".join(ret)

	def genVerilog(self,
		       genFunction=True,
		       name="crc",
		       inDataName="inData",
		       inCrcName="inCrc",
		       outCrcName="outCrc"):
		word = self.__gen(inDataName, inCrcName)
		ret = []
		ret.append("// vim: ts=4 sw=4 expandtab")
		ret.append("")
		ret.extend("// " + l for l in self.__header("Verilog").splitlines())
		ret.append("")
		if not genFunction:
			ret.append(f"`ifndef {name.upper()}_V_")
			ret.append(f"`define {name.upper()}_V_")
			ret.append("")
		ret.extend("// " + l for l in self.__algDescription().splitlines())
		ret.append("")
		if genFunction:
			ret.append(f"function automatic [{self.__nrCrcBits - 1}:0] {name};")
		else:
			ret.append(f"module {name} (")
		end = ";" if genFunction else ","
		ret.append(f"    input [{self.__nrCrcBits - 1}:0] {inCrcName}{end}")
		ret.append(f"    input [{self.__nrDataBits - 1}:0] {inDataName}{end}")
		if genFunction:
			ret.append("begin")
		else:
			ret.append(f"    output [{self.__nrCrcBits - 1}:0] {outCrcName}")
			ret.append(");")
		for i, bit in enumerate(word):
			assign = "" if genFunction else "assign "
			assignName = name if genFunction else outCrcName
			ret.append(f"    {assign}{assignName}[{i}] = {bit.gen_verilog()};")
		if genFunction:
			ret.append("end")
			ret.append("endfunction")
		else:
			ret.append("endmodule")
			ret.append("")
			ret.append(f"`endif // {name.upper()}_V_")
		return "\n".join(ret)

	def genVHDL(self,
		    name="crc",
		    inDataName="inData",
		    inCrcName="inCrc",
		    outCrcName="outCrc"):
		word = self.__gen(inDataName, inCrcName)
		ret = []
		ret.append(f"-- vim: ts=4 sw=4 expandtab")
		ret.append(f"")
		ret.extend(f"-- " + l for l in self.__header("VHDL").splitlines())
		ret.append(f"")
		ret.extend(f"-- " + l for l in self.__algDescription().splitlines())
		ret.append(f"")
		ret.append(f"library IEEE;")
		ret.append(f"use IEEE.std_logic_1164.all;")
		ret.append(f"")
		ret.append(f"entity {name} is")
		ret.append(f"    port (")
		ret.append(f"        {inCrcName}: in std_logic_vector({self.__nrCrcBits - 1} downto 0);")
		ret.append(f"        {inDataName}: in std_logic_vector({self.__nrDataBits - 1} downto 0);")
		ret.append(f"        {outCrcName}: out std_logic_vector({self.__nrCrcBits - 1} downto 0)")
		ret.append(f"    );")
		ret.append(f"end entity {name};")
		ret.append(f"")
		ret.append(f"architecture Behavioral of {name} is")
		ret.append(f"begin")
		for i, bit in enumerate(word):
			ret.append(f"    {outCrcName}({i}) <= {bit.gen_vhdl()};")
		ret.append(f"end architecture Behavioral;")
		return "\n".join(ret)

	def genMyHDL(self,
		     blockName="crc",
		     inDataName="inData",
		     inCrcName="inCrc",
		     outCrcName="outCrc"):
		word = self.__gen(inDataName, inCrcName)
		ret = []
		ret.append("# vim: ts=4 sw=4 expandtab")
		ret.append("")
		ret.extend("# " + l for l in self.__header("MyHDL").splitlines())
		ret.append("")
		ret.extend("# " + l for l in self.__algDescription().splitlines())
		ret.append("")
		ret.append("from myhdl import *")
		ret.append("")
		ret.append("@block")
		ret.append(f"def {blockName}({inCrcName}, {inDataName}, {outCrcName}):")
		ret.append("    @always_comb")
		ret.append("    def logic():")
		for i, bit in enumerate(word):
			ret.append(f"        {outCrcName}[{i}].next = {bit.gen_myhdl()}")
		ret.append("    return logic")
		ret.append("")
		ret.append("if __name__ == '__main__':")
		ret.append(f"    instance = {blockName}(")
		ret.append(f"        {inCrcName}=Signal(intbv(0)[{self.__nrCrcBits}:]),")
		ret.append(f"        {inDataName}=Signal(intbv(0)[{self.__nrDataBits}:]),")
		ret.append(f"        {outCrcName}=Signal(intbv(0)[{self.__nrCrcBits}:])")
		ret.append(f"    )")
		ret.append(f"    instance.convert(hdl='Verilog')")
		ret.append(f"    instance.convert(hdl='VHDL')")
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
		def makeCType(nrBits, name):
			if nrBits <= 8:
				cBits = 8
			elif nrBits <= 16:
				cBits = 16
			elif nrBits <= 32:
				cBits = 32
			elif nrBits <= 64:
				cBits = 64
			else:
				raise CrcGenError("C code generator: " + name + " sizes "
						  "bigger than 64 bit "
						  "are not supported.")
			return f"uint{cBits}_t"
		cCrcType = makeCType(self.__nrCrcBits, "CRC")
		cDataType = makeCType(self.__nrDataBits, "Input data")
		ret = []
		ret.append("// vim: ts=4 sw=4 expandtab")
		ret.append("")
		ret.extend("// " + l for l in self.__header("C").splitlines())
		ret.append("")
		if includeGuards:
			ret.append(f"#ifndef {funcName.upper()}_H_")
			ret.append(f"#define {funcName.upper()}_H_")
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
		extern = "extern " if declOnly else ""
		static = "static " if static and not declOnly else ""
		inline = "inline " if inline and not declOnly else ""
		end = ";" if declOnly else ""
		ret.append(f"{extern}{static}{inline}{cCrcType} "
			   f"{funcName}({cCrcType} {crcVarName}, {cDataType} {dataVarName}){end}")
		if not declOnly:
			ret.append("{")
			ret.append(f"    {cCrcType} ret;")
			for i, bit in enumerate(word):
				operator = "|=" if i > 0 else " ="
				ret.append(f"    ret {operator} ({cCrcType}){bit.gen_c()} << {i};")
			ret.append("    return ret;")
			ret.append("}")
			ret.append("#undef b")
		if includeGuards:
			ret.append("")
			ret.append(f"#endif /* {funcName.upper()}_H_ */")
		return "\n".join(ret)

	def runTests(self, name=None, extra=None):
		tmpdir = None
		try:
			import random
			rng = random.Random()
			rng.seed(424242)

			print(f"Testing{(' ' + name) if name else ''} "
			      f"P=0x{self.__P:X}, "
			      f"nrCrcBits={self.__nrCrcBits}, "
			      f"shiftRight={int(bool(self.__shiftRight))}, "
			      f"nrDataBits={self.__nrDataBits}"
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
			crcMask = (1 << self.__nrCrcBits) - 1
			dataMask = (1 << self.__nrDataBits) - 1
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
							polynomial=self.__P,
							nrCrcBits=self.__nrCrcBits,
							nrDataBits=self.__nrDataBits,
							shiftRight=self.__shiftRight)
						py = crc_pyimpl(crc, data)
						c = crc_cimpl(crc, data)
						if ref != py or ref != c:
							raise CrcGenError(
								f"Test failed: "
								f"P=0x{self.__P:X}, "
								f"nrCrcBits={self.__nrCrcBits}, "
								f"shiftRight={int(bool(self.__shiftRight))}, "
								f"nrDataBits={self.__nrDataBits}, "
								f"data=0x{data:X}, "
								f"ref=0x{ref:X}, "
								f"py=0x{py:X}, "
								f"c=0x{c:X}")
						crc = ref
						data = (data + 1) & dataMask
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
				p.append(f"x^{shift}")
		shift += 1
		poly >>= 1
	p.append(f"x^{nrBits}")
	return " + ".join(reversed(p))

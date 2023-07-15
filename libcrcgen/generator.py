# vim: ts=8 sw=8 noexpandtab
#
#   CRC code generator
#
#   Copyright (c) 2020-2023 Michael Büsch <m@bues.ch>
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
from libcrcgen.util import int2poly

__all__ = [
	"CrcGen",
	"CrcGenError",
]


@dataclass(frozen=True)
class AbstractBit:

	def flatten(self):
		return [self, ]

	def optimize(self, sortLex):
		pass


@dataclass(frozen=True)
class Bit(AbstractBit):
	name: str
	index: int

	def gen_python(self, level=0):
		return f"{self.name}[{self.index}]"

	def gen_c(self, level=0):
		return f"b({self.name}, {self.index})"

	def gen_verilog(self, level=0):
		return f"{self.name}[{self.index}]"

	def gen_vhdl(self, level=0):
		return f"{self.name}({self.index})"

	def gen_myhdl(self, level=0):
		return f"{self.name}[{self.index}]"

	def sortKey(self):
		return f"{self.name}_{self.index:07}"


@dataclass(frozen=True)
class ConstBit(AbstractBit):
	value: int

	def gen_python(self, level=0):
		return "1" if self.value else "0"

	def gen_c(self, level=0):
		return "1u" if self.value else "0u"

	def gen_verilog(self, level=0):
		return "1'b1" if self.value else "1'b0"

	def gen_vhdl(self, level=0):
		return 'b"1"' if self.value else 'b"0"'

	def gen_myhdl(self, level=0):
		return "1" if self.value else "0"

	def sortKey(self):
		return "1" if self.value else "0"


class XOR:
	__slots__ = (
		"__items",
	)

	def __init__(self, *items):
		self.__items = items

	def flatten(self):
		newItems = [ item
			     for subItem in self.__items
			     for item in subItem.flatten() ]
		self.__items = newItems
		return newItems

	def optimize(self, sortLex):
		newItems = []
		haveBits = {}
		constOnes = []
		for item in self.__items:
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
		self.__items = newItems

	def gen_python(self, level=0):
		return self.__gen("(", ")", level, " ^ ", lambda item: item.gen_python(level + 1))

	def gen_c(self, level=0):
		return self.__gen("(", ")", level, " ^ ", lambda item: item.gen_c(level + 1))

	def gen_verilog(self, level=0):
		return self.__gen("(", ")", level, " ^ ", lambda item: item.gen_verilog(level + 1))

	def gen_vhdl(self, level=0):
		return self.__gen("(", ")", level, " xor ", lambda item: item.gen_vhdl(level + 1))

	def gen_myhdl(self, level=0):
		return self.__gen("(", ")", level, " ^ ", lambda item: item.gen_myhdl(level + 1))

	def __gen(self, prefix, suffix, level, oper, itemGen):
		assert self.__items, "Empty XOR."
		if level == 0:
			prefix = suffix = ""
		return prefix + (oper.join(itemGen(item) for item in self.__items)) + suffix

	def sortKey(self):
		return "__".join(item.sortKey() for item in self.__items)


class Word:
	__slots__ = (
		"__items",
	)

	def __init__(self, *items):
		# items must be LSB first.
		self.__items = list(items)

	def __getitem__(self, index):
		return self.__items[index]

	def flatten(self):
		for item in self.__items:
			item.flatten()

	def optimize(self, sortLex):
		for item in self.__items:
			item.optimize(sortLex)


class CrcGenError(Exception):
	pass


class CrcGen:
	"""Combinatorial CRC algorithm generator.
	"""

	OPT_FLATTEN	 = 1 << 0  # Flatten the bit operation tree
	OPT_ELIMINATE	 = 1 << 1  # Eliminate redundant operations
	OPT_LEX		 = 1 << 2  # Sort the operands in lexicographical order where possible

	OPT_NONE	 = 0
	OPT_ALL		 = OPT_FLATTEN | OPT_ELIMINATE | OPT_LEX

	def __init__(self,
		     P,
		     nrCrcBits,
		     nrDataBits=8,
		     shiftRight=False,
		     optimize=OPT_ALL):
		self._P = P
		self._nrCrcBits = nrCrcBits
		self._nrDataBits = nrDataBits
		self._shiftRight = shiftRight
		self._optimize = optimize

	def __gen(self, dataVarName, crcVarName):
		nrCrcBits = self._nrCrcBits
		nrDataBits = self._nrDataBits
		P = self._P
		if nrCrcBits < 1 or nrDataBits < 1:
			raise CrcGenError("Invalid number of bits.")

		# Construct the function input data word.
		inData = Word(*(
			Bit(dataVarName, i)
			for i in range(nrDataBits)
		))

		# Construct the function input CRC word.
		inCrc = Word(*(
			Bit(crcVarName, i)
			for i in range(nrCrcBits)
		))

		# Helper function to XOR a polynomial bit with the data bit 'dataBit',
		# if the decision bit 'queryBit' is set.
		# This is done reversed, because the polynomial is constant.
		def xor_P(dataBit, queryBit, bitNr):
			if (P >> bitNr) & 1:
				return XOR(dataBit, queryBit)
			return dataBit

		# Helper function to optimize the algorithm.
		# This removes unnecessary operations.
		def optimize(word, sort=False):
			if self._optimize & self.OPT_FLATTEN:
				word.flatten()
			if self._optimize & self.OPT_ELIMINATE:
				word.optimize(sortLex=(sort and (self._optimize & self.OPT_LEX)))
			return word

		# Run the shift register for each input data bit.
		word = inCrc
		if self._shiftRight:
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
		pstr = int2poly(self._P, self._nrCrcBits, self._shiftRight)
		shift = "right (little endian)" if self._shiftRight else "left (big endian)"
		return (f"CRC polynomial coefficients: {pstr}\n"
			f"                             0x{self._P:X} (hex)\n"
			f"CRC width:                   {self._nrCrcBits} bits\n"
			f"CRC shift direction:         {shift}\n"
			f"Input word width:            {self._nrDataBits} bits\n")

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
		ret.append(f"            return (self.x >> i) & 1")
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
			ret.append(f"function automatic [{self._nrCrcBits - 1}:0] {name};")
		else:
			ret.append(f"module {name} (")
		end = ";" if genFunction else ","
		ret.append(f"    input [{self._nrCrcBits - 1}:0] {inCrcName}{end}")
		ret.append(f"    input [{self._nrDataBits - 1}:0] {inDataName}{end}")
		if genFunction:
			ret.append("begin")
		else:
			ret.append(f"    output [{self._nrCrcBits - 1}:0] {outCrcName}")
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
		ret.append(f"        {inCrcName}: in std_logic_vector({self._nrCrcBits - 1} downto 0);")
		ret.append(f"        {inDataName}: in std_logic_vector({self._nrDataBits - 1} downto 0);")
		ret.append(f"        {outCrcName}: out std_logic_vector({self._nrCrcBits - 1} downto 0)")
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
			ret.append(f"        {outCrcName}.next[{i}] = {bit.gen_myhdl()}")
		ret.append("    return logic")
		ret.append("")
		ret.append("if __name__ == '__main__':")
		ret.append(f"    instance = {blockName}(")
		ret.append(f"        {inCrcName}=Signal(intbv(0)[{self._nrCrcBits}:]),")
		ret.append(f"        {inDataName}=Signal(intbv(0)[{self._nrDataBits}:]),")
		ret.append(f"        {outCrcName}=Signal(intbv(0)[{self._nrCrcBits}:])")
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

		cCrcType = makeCType(self._nrCrcBits, "CRC")
		cDataType = makeCType(self._nrDataBits, "Input data")
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
				ret.append(f"    ret {operator} ({cCrcType})({bit.gen_c()}) << {i};")
			ret.append("    return ret;")
			ret.append("}")
			ret.append("#undef b")
		if includeGuards:
			ret.append("")
			ret.append(f"#endif /* {funcName.upper()}_H_ */")
		return "\n".join(ret)

#!/usr/bin/env python3
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

from crcgen import *

__all__ = [
	"main",
]

def main():
	import sys, argparse
	try:
		def argInt(string):
			if string.startswith("0x"):
				return int(string[2:], 16)
			return int(string)
		p = argparse.ArgumentParser()
		g = p.add_mutually_exclusive_group(required=True)
		g.add_argument("-p", "--python", action="store_true", help="Generate Python code")
		g.add_argument("-v", "--verilog-function", action="store_true", help="Generate Verilog function")
		g.add_argument("-m", "--verilog-module", action="store_true", help="Generate Verilog module")
		g.add_argument("-c", "--c", action="store_true", help="Generate C code")
		g.add_argument("-t", "--test", action="store_true", help="Run unit tests for the specified algorithm")
		g.add_argument("-T", "--polynomial-convert", type=str, help="Convert a polynomial from string to int or vice versa.")
		p.add_argument("-a", "--algorithm", type=str,
			       choices=CRC_PARAMETERS.keys(), default="CRC-32",
			       help="Select the CRC algorithm. "
				    "Individual algorithm parameters (e.g. polynomial) can be overridden with the options below.")
		p.add_argument("-P", "--polynomial", type=str, help="CRC polynomial")
		p.add_argument("-B", "--nr-bits", type=argInt, help="Number of bits (8-64)")
		g = p.add_mutually_exclusive_group()
		g.add_argument("-R", "--shift-right", action="store_true", help="CRC algorithm shift direction: right shift")
		g.add_argument("-L", "--shift-left", action="store_true", help="CRC algorithm shift direction: left shift")
		p.add_argument("-n", "--name", type=str, default="crc", help="Generated function/module name")
		p.add_argument("-D", "--data-param", type=str, default="data", help="Generated function/module data parameter name")
		p.add_argument("-C", "--crc-in-param", type=str, default="crcIn", help="Generated function/module crc input parameter name")
		p.add_argument("-o", "--crc-out-param", type=str, default="crcOut", help="Generated module crc output parameter name")
		p.add_argument("-S", "--static", action="store_true", help="Generate static C function")
		p.add_argument("-I", "--inline", action="store_true", help="Generate inline C function")
		p.add_argument("-O", "--optimize", type=argInt, default=CrcGen.OPT_ALL, help="Enable algorithm optimizer steps")
		args = p.parse_args()

		if (args.nr_bits is not None and
		    (args.nr_bits < 8 or args.nr_bits > 64)):
			raise CrcGenError("Invalid -B|--nr-bits argument. Valid range is 8-64.")

		if args.polynomial_convert is not None:
			if args.nr_bits is None:
				raise CrcGenError("-B|--nr-bits is required for -T|--polynomial-convert")
			try:
				if "^" in args.polynomial_convert.lower():
					print("0x%X" % poly2int(args.polynomial_convert,
								args.nr_bits,
								args.shift_right))
				else:
					print(int2poly(int(args.polynomial_convert, 0),
						       args.nr_bits,
						       args.shift_right))
			except ValueError as e:
				raise CrcGenError("-T|--polynomial-convert error: " + str(e))
			sys.exit(0)

		crcParameters = CRC_PARAMETERS[args.algorithm].copy()
		if args.nr_bits is not None:
			crcParameters["nrBits"] = args.nr_bits
		if args.shift_right:
			crcParameters["shiftRight"] = True
		if args.shift_left:
			crcParameters["shiftRight"] = False
		if args.polynomial is not None:
			try:
				if "^" in args.polynomial:
					polynomial = poly2int(args.polynomial,
							      crcParameters["nrBits"],
							      crcParameters["shiftRight"])
				else:
					polynomial = argInt(args.polynomial)
			except ValueError as e:
				raise CrcGenError("Polynomial error: " + str(e))
			crcParameters["polynomial"] = polynomial

		polynomial = crcParameters["polynomial"]
		nrBits = crcParameters["nrBits"]
		shiftRight = crcParameters["shiftRight"]

		if polynomial > ((1 << nrBits) - 1):
			raise CrcGenError("Invalid polynomial. "
					  "It is bigger than the CRC width "
					  "of (2**%d)-1." % nrBits)

		gen = CrcGen(P=polynomial,
			     nrBits=nrBits,
			     shiftRight=shiftRight,
			     optimize=args.optimize)
		if args.test:
			gen.runTests()
		else:
			if args.python:
				print(gen.genPython(funcName=args.name,
						    crcVarName=args.crc_in_param,
						    dataVarName=args.data_param))
			elif args.verilog_function:
				print(gen.genVerilog(genFunction=True,
						     name=args.name,
						     inDataName=args.data_param,
						     inCrcName=args.crc_in_param,
						     outCrcName=args.crc_out_param))
			elif args.verilog_module:
				print(gen.genVerilog(genFunction=False,
						     name=args.name,
						     inDataName=args.data_param,
						     inCrcName=args.crc_in_param,
						     outCrcName=args.crc_out_param))
			elif args.c:
				print(gen.genC(funcName=args.name,
					       crcVarName=args.crc_in_param,
					       dataVarName=args.data_param,
					       static=args.static,
					       inline=args.inline))
		sys.exit(0)
	except CrcGenError as e:
		print("ERROR: %s" % str(e), file=sys.stderr)
		sys.exit(1)

if __name__ == "__main__":
	main()

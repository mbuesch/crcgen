#!/usr/bin/env python3

import sys, os
basedir = os.path.abspath(os.path.dirname(__file__))

from libcrcgen.version import VERSION_STRING
from distutils.core import setup
import warnings

warnings.filterwarnings("ignore", r".*'long_description_content_type'.*")

with open(os.path.join(basedir, "README.rst"), "rb") as fd:
	readmeText = fd.read().decode("UTF-8")

setup(	name		= "crcgen",
	version		= VERSION_STRING,
	description	= "CRC algorithm code generator",
	license		= "GNU General Public License v2 or later",
	author		= "Michael Buesch",
	author_email	= "m@bues.ch",
	url		= "https://bues.ch/h/crcgen",
	scripts		= [
		"crcgen",
	],
	packages	= [
		"libcrcgen",
	],
	keywords	= "CRC Verilog VHDL MyHDL FPGA codegenerator",
	classifiers	= [
		"Development Status :: 5 - Production/Stable",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"Intended Audience :: Education",
		"Intended Audience :: Information Technology",
		"Intended Audience :: Science/Research",
		"Intended Audience :: Telecommunications Industry",
		"License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
		"License :: Public Domain",
		"Operating System :: OS Independent",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3",
		"Topic :: Education",
		"Topic :: Scientific/Engineering",
		"Topic :: Software Development",
		"Topic :: Software Development :: Code Generators",
		"Topic :: Utilities",
	],
	long_description=readmeText,
	long_description_content_type="text/x-rst",
)

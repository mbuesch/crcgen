# vim: ts=8 sw=8 noexpandtab
#
#   CRC code generator
#
#   Copyright (c) 2019-2021 Michael Buesch <m@bues.ch>
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

__all__ = [
	"CRC_PARAMETERS",
]

CRC_PARAMETERS = {
	"CRC-64-ECMA" : {
		"polynomial"	: 0xC96C5795D7870F42,
		"nrBits"	: 64,
		"shiftRight"	: True,
	},
	"CRC-64-ISO" : {
		"polynomial"	: 0xD800000000000000,
		"nrBits"	: 64,
		"shiftRight"	: True,
	},
	"CRC-32" : {
		"polynomial"	: 0xEDB88320,
		"nrBits"	: 32,
		"shiftRight"	: True,
	},
	"CRC-16" : {
		"polynomial"	: 0xA001,
		"nrBits"	: 16,
		"shiftRight"	: True,
	},
	"CRC-16-CCITT" : {
		"polynomial"	: 0x1021,
		"nrBits"	: 16,
		"shiftRight"	: False,
	},
	"CRC-8-CCITT" : {
		"polynomial"	: 0x07,
		"nrBits"	: 8,
		"shiftRight"	: False,
	},
	"CRC-8-IBUTTON" : {
		"polynomial"	: 0x8C,
		"nrBits"	: 8,
		"shiftRight"	: True,
	},
	"CRC-6-ITU" : {
		"polynomial"	: 0x03,
		"nrBits"	: 6,
		"shiftRight"	: False,
	},
}

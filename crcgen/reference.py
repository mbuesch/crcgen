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

__all__ = [
	"CrcReference",
]

class CrcReference(object):
	"""Generic CRC reference implementation.
	"""

	@classmethod
	def crc(cls, crc, data, polynomial, nrBits, shiftRight):
		mask = (1 << nrBits) - 1
		msb = 1 << (nrBits - 1)
		lsb = 1
		if shiftRight:
			tmp = (crc ^ data) & 0xFF
			for i in range(8):
				if tmp & lsb:
					tmp = ((tmp >> 1) ^ polynomial) & mask
				else:
					tmp = (tmp >> 1) & mask
			crc = ((crc >> 8) ^ tmp) & mask
		else:
			tmp = (crc ^ (data << (nrBits - 8))) & mask
			for i in range(8):
				if tmp & msb:
					tmp = ((tmp << 1) ^ polynomial) & mask
				else:
					tmp = (tmp << 1) & mask
			crc = tmp
		return crc

	@classmethod
	def crcBlock(cls, crc, data, polynomial, nrBits, shiftRight, preFlip, postFlip):
		mask = (1 << nrBits) - 1
		if preFlip:
			crc ^= mask
		for b in data:
			crc = cls.crc(crc, b, polynomial, nrBits, shiftRight)
		if postFlip:
			crc ^= mask
		return crc

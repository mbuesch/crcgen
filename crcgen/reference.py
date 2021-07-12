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
	"CrcReference",
]

from typing import Iterable

class CrcReference(object):
	"""Generic CRC reference implementation.
	"""

	@classmethod
	def crc(cls,
		crc: int,
		data: int,
		polynomial: int,
		nrCrcBits: int,
		nrDataBits: int = 8,
		shiftRight: bool = False):

		crcMask = (1 << nrCrcBits) - 1
		msb = 1 << (nrCrcBits - 1)
		lsb = 1
		if shiftRight:
			for i in range(nrDataBits):
				crc ^= data & 1
				data >>= 1
				if crc & lsb:
					crc = ((crc >> 1) ^ polynomial) & crcMask
				else:
					crc = (crc >> 1) & crcMask
		else:
			for i in range(nrDataBits):
				crc ^= ((data >> (nrDataBits - 1)) & 1) << (nrCrcBits - 1)
				data <<= 1
				if crc & msb:
					crc = ((crc << 1) ^ polynomial) & crcMask
				else:
					crc = (crc << 1) & crcMask
		return crc

	@classmethod
	def crcBlock(cls,
		     crc: int,
		     data: Iterable,
		     polynomial: int,
		     nrCrcBits: int,
		     nrDataBits: int = 8,
		     shiftRight: bool = False,
		     preFlip: bool  = False,
		     postFlip: bool = False):

		crcMask = (1 << nrCrcBits) - 1
		if preFlip:
			crc ^= crcMask
		for b in data:
			crc = cls.crc(crc=crc,
				      data=b,
				      polynomial=polynomial,
				      nrCrcBits=nrCrcBits,
				      nrDataBits=nrDataBits,
				      shiftRight=shiftRight)
		if postFlip:
			crc ^= crcMask
		return crc

# vim: ts=8 sw=8 noexpandtab
#
#   CRC code generator
#
#   Copyright (c) 2019-2022 Michael Buesch <m@bues.ch>
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

import re

__all__ = [
	"bitreverse",
	"poly2int",
	"int2poly",
]

def bitreverse(value, nrBits):
	"""Reverse the bits in an integer.
	"""
	ret = 0
	for _ in range(nrBits):
		ret = (ret << 1) | (value & 1)
		value >>= 1
	return ret

def poly2int(polyString, nrBits, shiftRight=False):
	"""Convert polynomial coefficient string to binary integer.
	"""
	polyString = polyString.lower().strip();
	if polyString.startswith("0x"):
		# Hex format
		try:
			poly = int(polyString[2:], 16)
		except ValueError:
			raise ValueError("Invalid polynomial coefficient format.")
	else:
		try:
			# Decimal format
			poly = int(polyString, 10)
		except ValueError:
			# Polynomial coefficient format
			polyString, _ = re.subn(r"\s+", "", polyString)
			poly = 0
			try:
				for bit in polyString.split("+"):
					if bit.startswith("x^"):
						poly |= 1 << int(bit[2:], 10)
					elif bit == "x":
						poly |= 1 << 1
					elif bit == "1":
						poly |= 1 << 0
					else:
						raise ValueError
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

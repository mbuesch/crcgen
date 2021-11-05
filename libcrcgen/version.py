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
	"VERSION_MAJOR",
	"VERSION_MINOR",
	"VERSION_EXTRA",
	"VERSION_STRING",
]

VERSION_MAJOR = 2
VERSION_MINOR = 2
VERSION_EXTRA = ""
VERSION_STRING = "%d.%d%s" % (VERSION_MAJOR, VERSION_MINOR, VERSION_EXTRA)

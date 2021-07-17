CRC algorithm code generator
============================

This tool generates synthesizable Verilog, VHDL or MyHDL code for use in FPGAs to calculate CRC (Cyclic Redundancy Check) checksums.


Example usage
=============

Display all options:

.. code:: sh

	crcgen -h


Generate Verilog code for CRC-32:

.. code:: sh

	crcgen -a CRC-32 -v


Generate VHDL code for CRC-32:

.. code:: sh

	crcgen -a CRC-32 -V


Generate Verilog code for a custom non-standard CRC or any standard algorithm that's not included in crcgen's -a list:

.. code:: sh

	crcgen -P "x^8 + x^7 + x^5 + x^4 + x^2 + x + 1" -B16 -R -v


License
=======

Copyright (c) 2019-2021 Michael Buesch <m@bues.ch>

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

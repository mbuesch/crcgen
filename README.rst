CRC algorithm HDL code generator (VHDL, Verilog, MyHDL)
=======================================================

`Homepage <https://bues.ch/h/crcgen>`_

`Git repository <https://bues.ch/cgit/crcgen.git>`_

`Github repository <https://github.com/mbuesch/crcgen>`_

This tool generates VHDL, Verilog or MyHDL code for use in FPGAs to calculate CRC (Cyclic Redundancy Check) checksums.

The generated HDL code is synthesizable and combinatorial. That means the calculation runs in one clock cycle on an FPGA.

Any combination of CRC algorithm parameters and polynomial coefficients can be selected.


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


Online crcgen
=============

An easy to use online version of crcgen that can be used without installing or downloading anything to your machine is available here:

`Online crcgen <https://bues.ch/h/crcgen>`_


License of the generated HDL code
=================================

The generated code is Public Domain.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE
USE OR PERFORMANCE OF THIS SOFTWARE.


License of the generator
========================

Copyright (c) 2019-2023 Michael Büsch <m@bues.ch>

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

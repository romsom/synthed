#-----------------------------------------------------------------------------
# Name:         k2000.py
# Purpose:      runtime scripting prototype
#
# Author:       John Bair
#               synthed.org
#
# Created:      2002/08/31
# RCS-ID:       $Id: k2000.py $
# Copyright:   Copyright (c) 2002 by John Bair. ALL RIGHTS RESERVED.
# License:     Released under GPL License
#
# This program is free software; you can redistribute it and/or modify it under 
# the terms of the GNU General Public License as published by the Free Software 
# Foundation; either version 2 of the License, or (at your option) any later 
# version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License 
# for more details.
# 
# You should have received a copy of the GNU General Public License 
# along with this program; if not, write to the Free Software Foundation, 
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
#-----------------------------------------------------------------------------

import struct
import wxPython.wx as wx

from instrument import *

# This is a sample instrument module. Typically an instrument will be specified 
# with an XML file to describe the UI and paramters, and any implementation or 
# behavior that is difficult to describe in XML can be implemented in a corresponding 
# instrument module.


# OnInit() will be executed immediately after an instrument module is imported
# This is a demo that shows some of the capabilities of runtime scripting
def OnInit():
    pass

# Todo: implement InTerm()
def OnTerm():
    'Executed when the script is unloaded'
    pass

    
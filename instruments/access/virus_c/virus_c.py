#-----------------------------------------------------------------------------
# Name:         virus_c.py
# Purpose:      runtime scripting prototype
#
# Author:       John Bair
#               synthed.org
#
# Created:      2002/31/08
# RCS-ID:       $Id: virus_c.py $
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

import os,stat,struct
from wx import wx

from instrument import *

# This is a sample instrument module. Typically an instrument will be specified 
# with an XML file to describe the UI and paramters, and any implementation or 
# behavior that is difficult to describe in XML can be implemented in a corresponding 
# instrument module.

# A sample function to show that the module is imported and executed
def OnShowMessage(event):
    'Show a message'
    dlg = wx.MessageDialog(application.main,'This is a runtime script','triton')
    dlg.ShowModal()
    dlg.Destroy()

# OnInit() will be executed immediately after an instrument module is imported
# This is a demo that shows some of the capabilities of runtime scripting
def OnInit():
    'Executed when the script is loaded'
    # Construct a menu
    menu = wx.Menu()
    # Add a menu item
    menu.Append(51,'S&how Message')
    # Insert the menu into the main menu
    application.main.menuBar.Insert(1,menu,'&Virus')
    # Bind a function to the menu item
    wx.EVT_MENU(application.main,51,OnShowMessage)

# Todo: implement OnTerm()
def OnTerm():
    'Executed when the script is unloaded'
    application.main.menuBar.Remove(1)

def FileReader(path):
    'Reads a Virus sysex file and returns a list of banks'
    banks = [VirusBank(0),VirusBank(1),VirusBank(2),VirusBank(3),VirusBank(4),
             VirusBank(5),VirusBank(6),VirusBank(7),VirusBank(8)]

    info = os.stat(path)
    length = info[stat.ST_SIZE]
    # Open file read binary
    # Todo: how to enable read sharing?
    file = open(path,'rb')
    # Sysex file has a header
    try:
        while file.tell() < length:
            ReadChunk(file,banks)
    finally:
        file.close()

    return banks

def ReadChunk(file,banks):
    'Read a chunk'
    header = file.read(5)
    if header == '\xF0\x00\x20\x33\x01':
        # Read the rest of the header
        buffer = file.read(2)
        if buffer[1] == '\x10' or buffer[1] == '\x11':
            bankNum = ord(file.read(1))
            patchNum = ord(file.read(1))
            dump = file.read(256)
            checksum = ord(file.read(1))
            eox = file.read(1)
            bank = banks[bankNum]
            bank.patches += [dump]
        else:
            # Todo: parse other dump types
            while file.read(1) <> '\xF7':
                pass

class VirusInstrument(Instrument):
    'Subclass of Instrument for Virus'
    def __init__(self,element,home,application):
        'Instrument constructor'
        Instrument.__init__(self,element,home,application)
        
    def OnParameterChange(param):
        return
        
class VirusBank(Bank):
    'Subclass of Bank for Virus'
    def __init__(self,bankNum):
            
        if bankNum == 0:
            bankType = 'multi'
        elif 1 <= bankNum <= 4:
            bankType = 'single'
        else:
            bankType = 'unknown'
        'Bank constructor'
        Bank.__init__(self,bankType,bankNum)
        if bankType == 'single':
            # single bank
            self.editable = 1
        elif bankType == 'multi':
            self.editable = 1
        # Todo: Make other banks editable
    
    def getBankName(self):
        'Return a bank name'
        if self.bankType == 'single':
            name = 'Single ' + self.getLetter()
        else:
            name = 'Multi'
        return name
        
    def getLetter(self):
        'Return a bank letter'
        return chr(ord('A') + self.bankNum - 1)
    
    def getPatchName(self,index):
        'Return name for the patch at index'
        name = ''
        patch = self.patches[index]
        if self.bankType == 'single':
            name = patch[240:250]
        elif self.bankType == 'multi':
            name = patch[4:13]
            
        return name
    
    def getPatchType(self,index):
        'Return type of patch'
        return self.bankType
    
# Custom encoder/decoder for filter env sustain time
class decode_filter_env_sustain_mode:
    def __init__(self,widget):
        self.widget = widget
        self.source = None
        
    def getData(self):
        filter_env_sustain_time = \
                                self.widget.env.attributes.get('filter_env_sustain_time')        
        v_level = self.widget.env.attributes.get('v_filter_env_sustain_level')
        v_time = self.widget.env.attributes.get('v_filter_env_sustain_time')
        
        value = filter_env_sustain_time.getData()
        if value == 63:
            # Sustain mode:
            # v_level = filter_env_sustain, t_time = 127
            filter_env_sustain =  self.widget.env.attributes.get('filter_env_sustain')
            v_level.setData(self.source,filter_env_sustain.getData())
            v_time.setData(self.source,value)
            return 0
        elif value < 63:
            # Fall mode:
            # v_level = 0, t_time = filter_env_sustain
            v_level.setData(self.source,0)
            v_time.setData(self.source,value)
            return 1
        else:
            # Rise mode:
            # v_level = 127, t_time = 127 - filter_env_sustain
            v_level.setData(self.source,127)
            v_time.setData(self.source,127-value)
            return 2

    def initData(self):
        self.getData()
        
    def setData(self,source,value):
        
        self.source = source
        
        # These are the surrogate parameters that we edit
        v_mode = self.widget.env.attributes.get('v_filter_env_sustain_mode')
        v_level = self.widget.env.attributes.get('v_filter_env_sustain_level')
        v_time = self.widget.env.attributes.get('v_filter_env_sustain_time')

        # This is the actual parameter we are editing
        filter_env_sustain_time =  self.widget.env.attributes.get('filter_env_sustain_time')

        v_mode.setData(source,value)

        if value == 0:
            # Sustain mode: 
            # filter_env_sustain_time = 63, v_level = filter_env_sustain, v_time = max
            filter_env_sustain_time.setData(source,63)
            filter_env_sustain = self.widget.env.attributes.get('filter_env_sustain')
            v_level.setData(source,filter_env_sustain.getData())
            v_time.setData(source,63)
        elif value == 1:
            # Fall mode: 
            # filter_env_sustain_time = v_time, v_level = 0
            filter_env_sustain_time.setData(source,v_time.getData())
            v_level.setData(source,0)
        else:
            # Rise mode: 
            # filter_env_sustain_time = v_time - 63, v_level = 127
            filter_env_sustain_time.setData(source,127-v_time.getData())
            v_level.setData(source,127)
        
    def getList(self):
        'Get the list of possible values for the widget'
        items = []
        valueList = self.widget.env.attributes.get('list_env_sustain_modes')
        if valueList:
            items = valueList.getList()
        return items
    
    def getVal(self,intval):
        v_filter_sustain_mode = self.widget.env.attributes.get('v_filter_env_sustain_mode')
        items = self.getList()
        return items[intval]

# Custom encoder/decoder for amp env sustain time
class decode_amp_env_sustain_mode:
    def __init__(self,widget):
        self.widget = widget
        self.source = None
        
    def getData(self):
        amp_env_sustain_time = \
                                self.widget.env.attributes.get('amp_env_sustain_time')        
        v_level = self.widget.env.attributes.get('v_amp_env_sustain_level')
        v_time = self.widget.env.attributes.get('v_amp_env_sustain_time')
        
        value = amp_env_sustain_time.getData()
        if value == 63:
            # Sustain mode:
            # v_level = amp_env_sustain, t_time = 127
            amp_env_sustain =  self.widget.env.attributes.get('amp_env_sustain')
            v_level.setData(self.source,amp_env_sustain.getData())
            v_time.setData(self.source,value)
            return 0
        elif value < 63:
            # Fall mode:
            # v_level = 0, t_time = amp_env_sustain
            v_level.setData(self.source,0)
            v_time.setData(self.source,value)
            return 1
        else:
            # Rise mode:
            # v_level = 127, t_time = 127 - amp_env_sustain
            v_level.setData(self.source,127)
            v_time.setData(self.source,127-value)
            return 2

    def initData(self):
        self.getData()
        
    def setData(self,source,value):
        
        self.source = source
        
        # These are the surrogate parameters that we edit
        v_mode = self.widget.env.attributes.get('v_amp_env_sustain_mode')
        v_level = self.widget.env.attributes.get('v_amp_env_sustain_level')
        v_time = self.widget.env.attributes.get('v_amp_env_sustain_time')

        # This is the actual parameter we are editing
        amp_env_sustain_time =  self.widget.env.attributes.get('amp_env_sustain_time')

        v_mode.setData(source,value)

        if value == 0:
            # Sustain mode: 
            # amp_env_sustain_time = 63, v_level = amp_env_sustain, v_time = max
            amp_env_sustain_time.setData(source,63)
            amp_env_sustain = self.widget.env.attributes.get('amp_env_sustain')
            v_level.setData(source,amp_env_sustain.getData())
            v_time.setData(source,63)
        elif value == 1:
            # Fall mode: 
            # amp_env_sustain_time = v_time, v_level = 0
            amp_env_sustain_time.setData(source,v_time.getData())
            v_level.setData(source,0)
        else:
            # Rise mode: 
            # amp_env_sustain_time = v_time - 63, v_level = 127
            amp_env_sustain_time.setData(source,127-v_time.getData())
            v_level.setData(source,127)
        
    def getList(self):
        'Get the list of possible values for the widget'
        items = []
        valueList = self.widget.env.attributes.get('list_env_sustain_modes')
        if valueList:
            items = valueList.getList()
        return items
    
    def getVal(self,intval):
        v_amp_sustain_mode = self.widget.env.attributes.get('v_amp_env_sustain_mode')
        items = self.getList()
        return items[intval]

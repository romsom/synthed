#-----------------------------------------------------------------------------
# Name:         triton.py
# Purpose:      runtime scripting prototype
#
# Author:       John Bair
#               synthed.org
#
# Created:      2002/31/08
# RCS-ID:       $Id: triton.py,v 1.7 2002/09/18 06:33:07 fumphco Exp $
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

# A sample function to show that the module is imported and executed
def OnShowMessage(event):
    'Show a message'
    dlg = wx.wxMessageDialog(application.main,'This is a runtime script','triton')
    dlg.ShowModal()
    dlg.Destroy()

# OnInit() will be executed immediately after an instrument module is imported
# This is a demo that shows some of the capabilities of runtime scripting
def OnInit():
    'Executed when the script is loaded'
    # Construct a menu
    menu = wx.wxMenu()
    # Add a menu item
    menu.Append(51,'S&how Message')
    # Insert the menu into the main menu
    application.main.menuBar.Insert(1,menu,'&Triton')
    # Bind a function to the menu item
    wx.EVT_MENU(application.main,51,OnShowMessage)

# Todo: implement InTerm()
def OnTerm():
    'Executed when the script is unloaded'
    application.main.menuBar.Remove(1)

def FileReader(path):
    'Reads a TRITON PCG file and returns a list of banks'
    banks = []
    # Open file read binary
    # Todo: how to enable read sharing?
    file = open(path,'rb')
    # PCG file has a 16 byte header
    header = file.read(16)
    if header == 'KORGP'+('\x00'*2)+'\x01'+('\x00'*8):
        # Read the first chunk that will indicate a PCG file format
        if file.read(4) == 'PCG1':
            # Next read the chunk length
            pcgLen = ReadInt(file)
            stop = file.tell() + pcgLen
            # Read to the end of the chunk
            while file.tell() < stop:
                # Read the nested chunk tyoe and length
                chunkType = file.read(4)
                chunkLen = ReadInt(file)
                # Global and Checksum chunks are special
                if chunkType == 'GLB1' or chunkType == 'CSM1':
                    bank = ReadSpecialChunk(file,chunkType,chunkLen)
                else:
                    # Read the chunk and return the bank list
                    bank = ReadChunks(file,chunkLen)
                    
                # Append bank(s) to the list
                if chunkType != 'CSM1':
                    banks += bank
                
    # Close the file when done
    # Todo: enclose above in try block to ensure that file close is always executed
    file.close()
    return banks

def ReadInt(file):
    'Reads a big-endian integer from the file and advances the current position'
    [intval] = struct.unpack('>i',file.read(4))
    return intval

def ReadSpecialChunk(file,chunkType,chunkLen):
    bank = TritonBank(chunkType,0)
    dump = file.read(chunkLen)
    bank.patches += [dump]
    return [bank]

def ReadChunks(file,chunkLen):
    'Reads one or more chunks'
    banks = []
    stop = file.tell() + chunkLen
    while file.tell() < stop:
        bank = ReadChunk(file)
        banks += [bank]
    return banks
                    
def ReadChunk(file):
    'Read a chunk'
    # Chunk type
    chunkType = file.read(4)
    # Chunk length
    chunkLen = ReadInt(file)
    # Number of patches in the chunk
    numPatches = ReadInt(file)
    # Length of a single patch
    patchLen = ReadInt(file)
    # Bank number
    bankNum = ReadInt(file)
    # Create the bank object
    bank = TritonBank(chunkType,bankNum)
    # Read and append the patches
    for i in range(numPatches):
        dump = file.read(patchLen)
        bank.patches += [dump]
    return bank

class TritonBank(Bank):
    'Subclass of Bank for KORG Triton'
    def __init__(self,bankType,bankNum):
        'TritonBank constructor'
        Bank.__init__(self,bankType,bankNum)
        if bankType == 'PBK1':
            # PROG bank
            self.editable = 1
        # Todo: Make COMBI, GLOB and other banks editable
        if bankType == 'CSM1':
             # some sort of unused checksum
            self.editable = 0
            self.visible = 0
    
    def getBankName(self):
        'Return a bank name'
        if self.bankType == 'PBK1':
            name = 'PROG ' + self.getLetter()
        elif self.bankType == 'MBK1':
            name = 'MOSS'
        elif self.bankType == 'CBK1':
            name = 'COMBI ' + self.getLetter()
        elif self.bankType == 'DBK1':
            name = 'DKIT'
        elif self.bankType == 'ABK1':
            name = 'ARP'
        elif self.bankType == 'GLB1':
            name = 'GLOBAL'
        else:
            name = self.bankType
        return name
        
    def getLetter(self):
        'Return a bank letter'
        return chr(ord('A') + self.bankNum)
    
    def getPatchName(self,index):
        'Return name for the patch at index'
        patch = self.patches[index]
        return patch[0:16]
    
    def getPatchType(self,index):
        'Return type of patch'
        type = ''
        
        if self.bankType == 'PBK1':
            patch = self.patches[index]
            byte = ord(patch[204]) & 3
            if byte < 3:
                type = 'pcm'
            elif byte == 3:
                type = 'moss'
        elif self.bankType == 'MBK1':
            type = 'moss'
        elif self.bankType == 'CBK1':
            type = 'combi' 
        elif self.bankType == 'DBK1':
            type = 'dkit'
        elif self.bankType == 'ABK1':
            type = 'arp'
        elif self.bankType == 'GLB1':
            type = 'glob'

        return type

# Custom encoder/decoder for realtime controls
# This is needed because two separate parameters are used.
# It also serves to test user-defined decoders.
class DecodeRealtimeControls:
    def __init__(self,widget):
        self.widget = widget
        
    def getData(self):
        msb = self.widget.env.attributes.get('COMMON_realtime_controls_msb')
        lsb = self.widget.env.attributes.get('COMMON_realtime_controls')
        value = msb*2 + lsb
        return value

    def setData(self,source,value):
        msb = self.widget.env.attributes.get('COMMON_realtime_controls_msb')
        lsb = self.widget.env.attributes.get('COMMON_realtime_controls')
        msb.setData(source,value&2)
        lsb.setData(source,value&1)
        
    def getList(self):
        'Get the list of possible values for the widget'
        items = []
        valueList = self.widget.env.attributes.get('list_realtime')
        if valueList:
            items = valueList.getList()
        return items
    
    def getVal(self,intval):
        return self.widget.getVal(intval)
    
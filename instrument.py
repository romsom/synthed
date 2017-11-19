#-----------------------------------------------------------------------------
# Name:        instrument.py
# Purpose:     The base instrument module
#
# Author:      John Bair 
#              jbair@synthed.org
#
# Created:     2002/08/11
# RCS-ID:      $Id: instrument.py,v 1.5 2002/09/18 06:33:07 fumphco Exp $
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

import array
import imp
import os
import sys

from wx import wx

from xml2obj import *

def ImportModule(name,application):
    'Import a module into the application namespace'
    module = None
    if name:
        # Import the module
        module = __import__(name)
        # Add some globals
        module.application = application
        # Run the OnInit() function
        if hasattr(module,'OnInit'):
            module.OnInit()
    return module

def LoadModule(name,file,filename,description,application):
    'Import a module into the application namespace'
    module = None
    # Import the module
    module = imp.load_module(name,file,filename,description)
    # Add some globals
    module.application = application
    # Run the OnInit() function
    if hasattr(module,'OnInit'):
        module.OnInit()
    return module

class Instrument:
    'Base instrument class'
    def __init__(self,element,home,application):
        'Instrument constructor'
        # Name added to attribute dictionary for this object
        self.id = element.getId()
        # Title for this instrument to display in title bars
        self.caption = element.getCaption()
        
        self.moduleName = ''
        self.module = None
        self.data = []
        self.decoders = []
        self.interfaces = []

        # Pathname of XML instrument definition
        self.path = os.path.normpath(element.getAttribute('path'))
        (directory,filename) = os.path.split(self.path)
        if not os.path.isdir(directory):
            self.path = os.path.normpath(os.path.join(home,self.path))
            (directory,filename) = os.path.split(self.path)
                 
        # chdir to the home directory
        oldDir = os.getcwd()
        try:
            os.chdir(directory)
    
            # Parse the instrument definition
            parser = Xml2Obj()
            self.element = parser.Parse(filename)

            # Load the module
            element = self.element.getFirstElement('module')
            self.moduleName = element.getAttribute('id')
            try:
                moduleInfo = imp.find_module(self.moduleName,[os.getcwd()])
            except:
                moduleInfo = imp.find_module(self.moduleName)
            (file,filename,description) = moduleInfo
            try:
                self.module = LoadModule(self.moduleName,file,filename,\
                                         description,application)
            finally:
                if file:
                    file.close()
            
            # Load the data maps
            elements = self.element.getFirstElement('data')
            for element in elements.getElements():
                path = element.getAttribute('path')
                data = parser.Parse(path)
                self.data.append(data)
            
            # Load the decoders
            elements = self.element.getFirstElement('decoders')
            for element in elements.getElements():
                path = element.getAttribute('path')
                decoder = parser.Parse(path)
                self.decoders.append(decoder)
            
            # Load the interfaces
            elements = self.element.getFirstElement('interfaces')
            for element in elements.getElements():
                path = element.getAttribute('path')
                interface = parser.Parse(path)
                self.interfaces.append(interface)
            
        finally:
            os.chdir(oldDir)
                
    def __del__(self):
        try:
            self.module.OnTerm()
        except:
            pass
    
    def GetPatchInfo(self,type):
        for element in self.data:
            #print("element:")
            print(element)
            for patch in element.getElements('patch'):
                #print("found matching element")
                print(patch.getId())
                #print(type)
                if patch.getId() == type:
                    return patch

    def GetInterfaceInfo(self,type):
        for interfaces in self.interfaces:
            modes = interfaces.Search('mode',type)
            if modes:
                return modes[0]

class Bank:
    'Bank class that can be subclassed to support specific synths'
    def __init__(self,bankType,bankNum):
        'Bank constructor'
        # Type of bank (i.e. prog, combi, global, etc.)
        self.bankType = bankType
        # Bank number
        self.bankNum = bankNum
        # This list of patches contained in this bank
        self.patches = []
        # Will this bank appear in the bank list
        self.visible = 1
        # Can a patch editor be opened on patches in this bank
        self.editable = 0
        
    def getBankName(self):
        'Override this to return the bank name'
        return self.bankType + ':' + str(self.bankNum)
    
    def getPatchName(self,index):
        'Override this to return the patch name'
        return ''
    
    def getPatchType(self,index):
        'Override this to return the patch type'
        return ''

class Patch:
    'Wrapper for a byte array'
    def __init__(self,offset=0):
        self.data = array.array('B')
        # patch addresses are relative to self.offset
        self.offset = offset

    def fromstring(self,strval):
        # set the values
        self.data.fromstring(strval)
        
    def tostring(self):
        return self.data.tostring()
        
    def set(self,offset,value):
        # set the new value at the specified offset
        self.data[self.offset+offset] = value
        
    def get(self,offset):
        return self.data[self.offset+offset]
    

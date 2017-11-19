#-----------------------------------------------------------------------------
# Name:        synthed.py
# Purpose:     Synthesizer Editor and Librarian
#
# Author:      John Bair
#
# Created:     2002/08/13
# RCS-ID:      $Id: synthed.py,v 1.13 2002/09/20 08:16:12 fumphco Exp $
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

"""
This module contains the main application, parent MDI frame and some other 
classes and methods that are called by the parent frame.
"""

import array,os,string,sys,time,traceback
from wx import wx
from xml.parsers import expat

from __version__ import ver
from instrument import *
from editor import *
from parameter import *

appname = 'SynthEd '+ver
SYNTHED_HOME = ''

class SynthEd(wx.MDIParentFrame):
    'SynthEd Parent frame'
    def __init__(self,parent,id,title,pos,size):
        'SynthEd constructor'
        wx.MDIParentFrame.__init__(self,parent,id,title,pos,size)
        
        # Add menus, tool bar and status bar
        self.CreateMenu()
        self.CreateToolBar()
        self.statusBar = self.CreateStatusBar()

        # Load configuration file
        self.config = SynthEdConfig()
        self.LoadConfig()
        self.LoadInsSubMenu()
        self.LoadDesignSubMenu()
        
        # Synthdev is loaded later
        self.synthdev = None
        
        # populate the submenus
        #self.LoadInsSubMenu()
        #self.LoadDesignSubMenu()
        
    def CreateMenu(self):
        'Add a standard set of menus'
        # Todo: move this to a resource file?
        
        # File menu
        self.fileMenu = wx.Menu()
        self.fileMenu.Append(10,'&New')
        self.fileMenu.Enable(10,False)
        self.fileMenu.Append(11,'&Open')
        self.fileMenu.Append(12,'&Close')
        self.fileMenu.Enable(12,False)
        self.fileMenu.AppendSeparator()
        self.fileMenu.Append(13,'&Save')
        self.fileMenu.Enable(13,False)
        self.fileMenu.Append(14,'Save &As...')
        self.fileMenu.Enable(14,False)
        self.fileMenu.AppendSeparator()
        self.fileMenu.Append(19,'E&xit')
        
        # View menu
        self.viewMenu = wx.Menu()
        self.insSubMenu = wx.Menu()
        self.viewMenu.AppendMenu(20,'&Instrument',self.insSubMenu)
        self.viewMenu.AppendSeparator()
        self.viewMenu.Append(21,'&Toolbars')
        self.viewMenu.Enable(21,False)
        self.viewMenu.Append(22,'&Status bar')
        self.viewMenu.Enable(22,False)
        self.viewMenu.AppendSeparator()
        self.viewMenu.Append(29,'&Options...')
        self.viewMenu.Enable(29,False)
        
        # Tools menu
        self.toolsMenu = wx.Menu()
        self.designSubMenu = wx.Menu()
        self.toolsMenu.AppendMenu(30,'&Design',self.designSubMenu)
        self.toolsMenu.AppendSeparator()
        self.toolsMenu.Append(31,'&Shell')
        
        # Help menu
        self.helpMenu = wx.Menu()
        self.helpMenu.Append(90,'&Help')
        self.helpMenu.Append(91,'&About')
        
        # Menu bar
        self.menuBar = wx.MenuBar()
        self.menuBar.Append(self.fileMenu,'&File')
        self.menuBar.Append(self.viewMenu,'&View')
        self.menuBar.Append(self.toolsMenu,'&Tools')
        self.menuBar.Append(self.helpMenu,'&Help')
        self.SetMenuBar(self.menuBar)
        
        # Bind menu items
        wx.EVT_MENU(self,11,self.OnOpen)
        wx.EVT_MENU(self,20,self.OnInstrument)
        wx.EVT_MENU(self,30,self.OnDesign)
        #wx.EVT_MENU(self,31,self.OnShell)
        wx.EVT_MENU(self,19,self.OnQuit)
        wx.EVT_MENU(self,91,self.OnAbout)

    def LoadConfig(self):
        'Load configuration file'
        try:
            global SYNTHED_HOME
            SYNTHED_HOME = os.environ['SYNTHED_HOME']
        except:
            message = 'Could not find the SYNTHED_HOME environment variable.\n'
            ShowMessage(self,message,wx.OK)
            self.Destroy()
        
        # The config.xml file will be in the SYNTHED_HOME directory
        path = os.path.join(SYNTHED_HOME,'config.xml')
        
        wx.BeginBusyCursor()
        # chdir to the home directory
        oldDir = os.getcwd()
        os.chdir(SYNTHED_HOME)
        try:
            self.config.LoadConfig(path)
        except:
            message = 'Could not open the configuration file:\n' +\
                path+'\n'+\
                'Please check the SYNTHED_HOME environment variable.\n'
            ShowError(self,wx.OK)

        # chdir back
        os.chdir(oldDir)
        
        wx.EndBusyCursor()

    def LoadInsSubMenu(self):
        'Create a menu item for each instrument'
        instruments = self.config.GetInstruments()
        id = 200
        for instrument in instruments.getElements():
            self.insSubMenu.Append(id,instrument.getCaption())
            if instrument.getId() == 'synthdev':
                self.insSubMenu.Enable(id,False)
            wx.EVT_MENU(self,id,self.OnInstrument)
            id += 1
                        
    def LoadDesignSubMenu(self):
        'Create a menu item for each instrument'
        instruments = self.config.GetInstruments()
        id = 300
        for instrument in instruments.getElements():
            self.designSubMenu.Append(id,instrument.getCaption())
            if instrument.getId() == 'synthdev':
                self.designSubMenu.Enable(id,False)
            wx.EVT_MENU(self,id,self.OnInstrument)
            id += 1
            
        self.designSubMenu.AppendSeparator()
        self.designSubMenu.Append(id,'&New')
        self.designSubMenu.Enable(id,False)
        id += 1
                        
    def OnAbout(self,event):
        ShowMessage(self,appname+'\nOSI Certified Open Source Software')
    
    def OnInstrument(self,event):
        'Open an instrument patch editor'
        # Compute index into the instruments list
        eventId = event.GetId()
        if eventId >= 300:
            # This is a designSubMenu selection
            design = 1
        else:
            # This is an insSubMenu selection
            design = 0
        index = eventId - int(eventId/100) * 100
                
        # SynthDev definition is used in design mode
        if not self.synthdev:
            element = self.config.GetInstrumentById('synthdev')
            self.synthdev = Instrument(element,SYNTHED_HOME,application)

        # Get the XML element
        instruments = self.config.GetInstruments()
        element = instruments.children[index]
        print("instrument element: ")
        print(element.children)
        
        # Construct an Instrument object
        instrument = Instrument(element,SYNTHED_HOME,application)
        if instrument:
            wx.BeginBusyCursor()
            
            # Create a dummy patch
            patch = Patch()
            patch.fromstring('\x00'*1024)
            
            # Open a patch editor
            child = PatchEditor(self,-1,instrument.caption,patch,\
                                None,instrument,self.synthdev,design)
            wx.EndBusyCursor()
            
    def OnDesign(self,event):
        pass
            
    def OnOpen(self,event):
        'Open and load a synth file'
        # File types and associations are configurable
        wildcards = self.config.GetWildCards()

        # SynthDev definition is used in design mode
        if not self.synthdev:
            element = self.config.GetInstrumentById('synthdev')
            self.synthdev = Instrument(element,SYNTHED_HOME,application)

        # Display a wxFileDialog
        path = ''        
        dlg = wx.FileDialog(None,'Open a file','','',wildcards,wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        
        if path:
            start = time.clock()
            # Get the instrument assciated with this file type
            # Todo: Use mime manager instead?
            element = self.config.GetInstrumentByAssociation(path)
            instrument = Instrument(element,SYNTHED_HOME,application)
            if instrument:
                wx.BeginBusyCursor()
                # Construct a bank editor for the file
                child = BankEditor(self,-1,instrument,self.synthdev,path)
                stop = time.clock()
                self.statusBar.SetStatusText('%5.2f seconds' % (stop-start))
                wx.EndBusyCursor()
            else:
                ShowMessage(self,'The file:\n\t' +\
                            path + '\nis not associated with an instrument.')
                
    def OnShell(self,event):
        'Shell for debugging'
        try:
            wx.BeginBusyCursor()
            # Create a child frame
            child = wx.MDIChildFrame(self,-1,'Python Shell')
            # Shell
            win = wx.py.shell.Shell(child, -1, style=wx.wxCLIP_CHILDREN,locals=globals())
            win.SetFocus()
            
            wx.EndBusyCursor()
        except:
            wx.EndBusyCursor()
            ShowError(self)
        
    def OnQuit(self,event):
        'Cleanup and quit'
        self.Destroy()
        
class BankEditor(wx.MDIChildFrame):
    'Bank Editor'
    def __init__(self,parent,id,instrument,synthdev,path):
        'BankEditor constructor'
        # Initialize attributes
        self.mdiParent = parent
        self.path = path
        self.banks = None
        self.instrument = instrument
        self.synthdev = synthdev
        
        self.bankList = None
        self.patchList = None
        self.x = 0
        self.y = 0
        
        # Base class
        wx.MDIChildFrame.__init__(self,parent,id,instrument.caption)
        
        'Parse the file and load the bank list'
        self.banks = self.instrument.module.FileReader(self.path)
        if len(self.banks) > 1:
            
            # Put a splitter in the frame
            self.vertsplit = wx.SplitterWindow(self,-1)
            
            # Bank list on the left
            self.bankList = wx.ListBox(self.vertsplit,-1,style=wx.SIMPLE_BORDER)
            bankListId = self.bankList.GetId()
            
            # Patch list on the right
            self.patchList = wx.ListCtrl(self.vertsplit,-1,\
               style=wx.LC_LIST|wx.LC_EDIT_LABELS)
            
            self.vertsplit.SplitVertically(self.bankList, self.patchList, 160)
            
            wx.EVT_LISTBOX(self,bankListId,self.OnBankSelect)
            
            # Populate the bank list
            self.AddBanks()
        
            # Automatically select the first bank
            self.bankList.SetSelection(0)
        else:
            # Patch list on the right
            self.patchList = wx.ListCtrl(self,-1,size=self.GetClientSize(),\
               style=wx.LC_LIST|wx.LC_EDIT_LABELS)
            
        patchListId = self.patchList.GetId()
        
        # Event handlers
        wx.EVT_LIST_ITEM_ACTIVATED(self,patchListId,self.OnPatchActivate) 

        EVT_RIGHT_DOWN(self.patchList, self.OnRightDown)

        # for wxMSW
        wx.EVT_COMMAND_RIGHT_CLICK(self.patchList, self.patchList.GetId(), \
                                   self.OnRightClick)

        # for wxGTK
        wx.EVT_RIGHT_UP(self.patchList, self.OnRightClick)

        # Populate the patch list
        self.AddPatches(0)

    def OnBankSelect(self,event):
        'Display the list of patches for the selected bank'
        self.patchList.ClearAll()
        self.AddPatches(self.bankList.GetSelection())
        
    def AddBanks(self):
        for bank in self.banks:
            if bank.visible:
                self.bankList.Append(bank.getBankName())
            
    def AddPatches(self,bankNum):
        'Populate the patch list for a bank'
        bank = self.banks[bankNum]
        num = len(bank.patches)
        for i in range(num):
            strval = '%03d:%s' % (i,bank.getPatchName(i))
            self.patchList.InsertStringItem(i,strval)

    def OnPatchActivate(self,event):
        'Open a patch editor when a patch is double-clicked'
        if self.bankList:
            bankNum = self.bankList.GetSelection()
        else:
            bankNum = 0
        patchNum = event.GetIndex()
        patchName = event.GetText()
        bank = self.banks[bankNum]
        
        # Only open a patch editor if the bank is marked editable
        if bank.editable:
            patchType = bank.getPatchType(patchNum)
            # Get the right patch
            patch = bank.patches[patchNum]
            data = Patch()
            data.fromstring(patch)

            # Construct and display the patch editor
            child = PatchEditor(self.mdiParent,-1,\
                patchName,data,patchType,self.instrument,self.synthdev)

    def OnRightDown(self,event):
        self.x = event.GetX()
        self.y = event.GetY()
        event.Skip()

    def OnRightClick(self, event):
        menu = wx.Menu()

        menu.Append(0,'Cu&t')
        menu.Append(1,'&Copy')
        menu.Append(2,'&Paste')
        menu.AppendSeparator()
        menu.Append(4,'&Delete')
        menu.Append(5,'&Rename')
        #EVT_MENU(self, 0, self.OnListCopy)
        #EVT_MENU(self, 1, self.OnListCut)
        #EVT_MENU(self, 2, self.OnListPaste)
        #EVT_MENU(self, 3, self.OnListClear)
        #EVT_MENU(self, 4, self.OnListDelete)
        #EVT_MENU(self, 5, self.OnListRename)
        (x,y) = self.patchList.GetPositionTuple()
        self.PopupMenu(menu,(x+self.x, y+self.y))
        menu.Destroy()
        event.Skip()

class SynthEdConfig:
    'SynthEd Configuration'
    def __init__(self):
        'SynthEdConfig constructor'
        self.root = None

    def LoadConfig(self,filename):
        parser = Xml2Obj()
        self.root = parser.Parse(filename)
        
    def GetWildCards(self):
        wildcards = ''
        # Get the list of <file> elements
        files = self.root.getFirstElement('files')
        for fileNode in files.getElements():
            wildcard = fileNode.getAttribute('wildcard','')
            if wildcards:
                wildcards += '|'
            wildcards += wildcard
        if wildcards:
            wildcards += '|'
        wildcards += 'All files (*.*)|*.*'
        return wildcards
    
    def GetInstruments(self):
        'Get a list of supported instruments'
        instruments = self.root.getFirstElement('instruments')
        return instruments
        
    def GetInstrumentById(self, id):
        instrument = None
        
        'Get a list of supported instruments'
        instruments = self.root.getFirstElement('instruments')
        for element in instruments.getElements():
            if element.getId() == id:
                instrument = element
                break
            
        return instrument
        
    def GetInstrumentByAssociation(self,path):
        'Find the instrument that is associated with this file suffix'
        instrument = None
        
        # Try to follow O/S path case convention
        normedPath = os.path.normcase(os.path.normpath(path))
        
        # Get <files> and <lists>
        files = self.root.getFirstElement('files')
        instruments = self.root.getFirstElement('instruments')

        # Check if the suffix matches the passed filename
        for fileNode in files.getElements():
            suffix = fileNode.getAttribute('suffix')
            suffixLen = len(suffix)
            if normedPath[-suffixLen:] == suffix:
                # Matching suffix so get the associated instrument
                ref = fileNode.getAttribute('instrument')
                for instrumentNode in instruments.getElements():
                    if ref == instrumentNode.getId():
                        instrument = instrumentNode
                        break
        return instrument
                        
class App(wx.App):
    'The App'
    def OnInit(self):
        wx.InitAllImageHandlers()
        self.main = SynthEd(None,wx.NewId(),appname,\
                                     wx.DefaultPosition,wx.DefaultSize)

        # Ensure frame is of a reasonable size
        (width,height) = self.main.GetClientSizeTuple()
        if width < 800 or height < 600:
            self.main.SetClientSize((800,600))
            
        self.main.Center()
        self.main.Show()
        return True

# Utility functions that should be moved to a utilities module
def ShowMessage(parent,message,style=wx.OK):
    'Display a message box'
    dlg = wx.MessageDialog(parent,message,appname,style)
    intval = dlg.ShowModal()
    dlg.Destroy()
    return intval
    
def ShowError(parent,style=wx.OK):
    'Display an exception and traceback in a message box'
    message = ''
    TBStrings = traceback.format_exception(*sys.exc_info())
    for line in TBStrings:
        message += (line)
    dlg = wx.MessageDialog(parent,message,appname,style)
    intval = dlg.ShowModal()
    dlg.Destroy()
    return intval

def HexDump(data):
    'Quick and dirty hex dump'
    hexdump = ''
    offset = 0
    for byte in data:
        if offset % 16 == 0:
            if offset > 0:
                hexdump += '\n'
            hexdump += '%04d:%04X ' % [offset,offset]
        hexdump += '%02X' % ord(data[offset])
    return hexdump

# Main application starts here
#Some debuggers won't work if the next line is uncommented
if __name__ == '__main__':
    application = App()
    application.MainLoop()

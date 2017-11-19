#-----------------------------------------------------------------------------
# Name:        editor.py
# Purpose:     Synthesizer Editor
#
# Author:      John Bair 
#              jbair@synthed.org
#
# Created:     2002/08/11
# RCS-ID:      $Id: editor.py,v 1.8 2002/09/21 07:59:06 fumphco Exp $
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

import array,os,string,sys,time,traceback
from wx import wx
from wx import html
from xml.parsers import expat

from __version__ import ver
from parameter import *
from tag import *

appname = 'SynthEd '+ver

class PatchEditor(wx.MDIChildFrame):
    'Patch Editor'
    def __init__(self,parent,id,title,patch,patchType,instrument,\
                 synthdev,design=0):
        print("patchtype in editor (init): " + patchType)
        'PatchEditor constructor'
        wx.MDIChildFrame.__init__(self,parent,id,title)
        
        # These are stored for debugging convenience
        self.patch = patch
        self.patchType = patchType
        self.instrument = instrument
        self.synthdev = synthdev
        self.design = design
        
        # Put a splitter in the frame
        self.vertsplit = wx.SplitterWindow(self,-1)
        
        # Populate the splitter with two scrolling panes
        self.horizsplit = wx.SplitterWindow(self.vertsplit,-1)
        self.right = PatchEditBook(self.vertsplit,-1,instrument,patch)
        self.vertsplit.SplitVertically(self.horizsplit, self.right, 160)
        
        # Split the left pane between a tree control and a property editor
        self.tree = PatchEditTree(self.horizsplit,self.instrument,\
                              self.right,self.patch,self.patchType,self.design)
        self.property = PropertyEditor(self.horizsplit,-1,self.synthdev)
        self.tree.SetPropertyEditor(self.property)
        self.horizsplit.SplitHorizontally(self.tree, self.property, 200)
        
        # Parse the instrument definition and load the tree
        start = time.clock()
        wx.BeginBusyCursor()
        self.tree.LoadPatch()
        if not self.design:
            self.tree.ExpandTree()
        wx.EndBusyCursor()
        stop = time.clock()
        # Todo: remove this timing info?
        statusBar = instrument.module.application.main.statusBar
        statusBar.SetStatusText('%5.2f seconds' % (stop-start))

class PatchEditTree(wx.TreeCtrl):
    'Patch editor tree control is used to select pages in the patch editor'
    def __init__(self,parent,instrument,editor,patch,patchType,design):
        print("patchtype on init: " + patchType)
        'PatchEditTree constructor'
        wx.TreeCtrl.__init__(self,parent,-1,style=wx.SIMPLE_BORDER)
        # Initialize attributes
        self.instrument = instrument
        self.env = SynthEnv()
        self.patch = patch
        self.patchType = patchType
        self.design = design
        self.property = None
        
        # Save a reference to the editor pane
        self.editor = editor
        
        # elementStack is used to track nesting of all elements
        self.rootElement = None
        self.elementStack = []

        # allNodes is a quick list for expanding all nodes
        self.allNodes = []
        
        # Trees need an image list to do Drag and Drop
        self.il = wx.ImageList(16,16)
        self.SetImageList(self.il)
        
        # Event handlers
        wx.EVT_TREE_SEL_CHANGED(self,self.GetId(),self.OnTreeItemSelect)
        
    def OnTreeItemSelect(self,event):
        'Possibly edit the selected tree item'
        # Get the selected item
        itemid = self.GetSelection()
        element = self.GetPyData(itemid)
        
        # Edit the selected element
        if element and element.name == 'page':
            wx.BeginBusyCursor()
            # Hide the editor
            self.editor.Show(False)
            
            # Clear dictionary and map
            self.env.Clear()
            
            # Delete existing tabs
            self.editor.DeleteAllTabs()
            try:
                # Get the list of <tab> elements for this page
                for tabElement in element.getElements('tab'):
                    # Add and populate the tab
                    self.editor.AddTab(self.env,tabElement)
                # Set the initial enabled states
                tab = self.editor.GetPage(0)
                tab.Load()
            except:
                ShowError(self)
                self.editor.DeleteAllTabs()
                
            # The environment is now initialized
            # Widget notifications are now enabled
            self.env.initialized = 1
            self.env.eventHandler = self.editor
            
            # Show the editor
            self.editor.Show(True)
            wx.EndBusyCursor()
        elif element and element.name == 'list':
            # Cannot edit sublists
            if element.getElements('list'):
                return
            
            wx.BeginBusyCursor()
            # Hide the editor
            self.editor.Show(False)
            
            # Clear dictionary and map
            self.env.Clear()
            
            # Delete existing tabs
            self.editor.DeleteAllTabs()
            try:
                # Get the list of <tab> elements for this page
                self.editor.AddListTab(self.env,element)
            except:
                ShowError(self)
                self.editor.DeleteAllTabs()
                
            # Show the editor
            self.editor.Show(True)
            wx.EndBusyCursor()

        if element and self.property:
            # Properties editor
            self.property.UpdatePropertyList(element,self.design)
            
    def LoadPatch(self):
        'Populate the tree for patch editing'
        # Add module to dictionary so that it can be referenced
        dictionary = self.env.attributes
        dictionary.update({self.instrument.moduleName:self.instrument.module})
        self.env.instrument = self.instrument

        # Find the matching patch description
        patchInfo = self.instrument.GetPatchInfo(self.patchType)
            
        # Instantiate the params
        for element in patchInfo.getElements():
            param = Param(self.env,element,self.patch)
            dictionary.update({param.getId():param})
            #setattr(self.env.module,param.getId(),param)
                
        # Instantiate the decoders
        for documents in self.instrument.decoders:
            for decoders in documents.getElements():
                for decoder in decoders.getElements():
                    if decoder.name == 'list':
                        element = ValueList(decoder.name,decoder.attributes,\
                                            decoder.getElements())
                    elif decoder.name == 'scale':
                        element = ValueScale(decoder.name,decoder.attributes,\
                                             decoder.getElements())
                    id = element.getId()
                    dictionary.update({id:element})
                    #setattr(self.env.module,id,element)
                
        # Find the associated interface
        mode = self.instrument.GetInterfaceInfo(self.patchType)

        # Instantiate the interface
        if mode:
            self.rootElement = mode
            caption = mode.getCaption()
            root = self.AddRoot(caption)
            self.allNodes.append(root)
            for element in mode.getElements('page'):
                caption = element.getCaption()
                itemId = self.AppendItem(root,caption)
                self.SetPyData(itemId,element)
                self.allNodes.append(itemId)
        
    def ExpandTree(self):
        'Expand all tree nodes'
        self.Freeze()
        for item in self.allNodes:
            self.Expand(item)
        self.Thaw()
        
    def SetPropertyEditor(self,property):
        self.property = property
        self.env.property = property
        
class PropertyEditor(wx.Panel):
    def __init__(self,parent,id,synthdev):
        wx.Panel.__init__(self,parent,id)

        self.element = None
        self.properties = []
        self.design = 0
        self.modified = 0
        
        try:
            self.synthdev = synthdev.interfaces[0]
            self.dictionary = self.synthdev.Index()
        except:
            self.dictionary = {}
        
        # Main sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Top section with two buttons and textCtrl
        self.topSizer = wx.BoxSizer(wx.HORIZONTAL)
    
        try:
            tickArt = wx.wxArtProvider_GetBitmap(wx.wxART_TICK_MARK)
            crossArt = wx.wxArtProvider_GetBitmap(wx.wxART_CROSS_MARK)
            self.okButton = wx.wxBitmapButton(self,-1,tickArt,(-1,-1),(20,5))
            self.cancelButton = wx.wxBitmapButton(self,-1,crossArt,\
                                                  (-1,-1),(20,5))
        except:
            self.okButton = wx.Button(self,-1,'/',(-1,-1),(20,5))
            self.cancelButton = wx.Button(self,-1,'X',(-1,-1),(20,5))
            
        self.okButton.Enable(0)
        self.cancelButton.Enable(0)
    
        self.topSizer.AddWindow(self.okButton,0,wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND,3)
        self.topSizer.AddWindow(self.cancelButton,0,wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND,3)
    
        self.valueText = wx.TextCtrl(self,-1,'',style=wx.PROCESS_ENTER)
        self.valueText.Enable(False)
        self.topSizer.AddWindow(self.valueText,1,wx.ALL|wx.EXPAND,3)
        
        self.sizer.AddSizer(self.topSizer,0,wx.EXPAND)
    
        # Middle section with two list boxes
        self.middleSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.valueList = wx.ListBox(self,-1,(-1,-1),(-1,60))
        self.valueList.Show(False);
        self.propertyScrollingList = wx.ListBox(self,-1,(-1,-1),(100,100))
        self.middleSizer.AddWindow(self.propertyScrollingList,1,\
                                   wx.ALL|wx.EXPAND,3)
    
        self.sizer.AddSizer(self.middleSizer,1,wx.EXPAND)
        
        guiFont = self.propertyScrollingList.GetFont()
        pointSize = guiFont.GetPointSize()
        fixedFont = wx.Font(pointSize,wx.TELETYPE,wx.NORMAL,wx.NORMAL)
        self.propertyScrollingList.SetFont(fixedFont)

        # Todo: Bottom with buttons 
        
        self.SetSizer(self.sizer)        
        self.Layout()

        # Event handlers
        wx.EVT_LISTBOX(self,self.propertyScrollingList.GetId(),\
                       self.OnSelectProperty)
        
    def ShowTextControl(self,show):
        self.valueText.Show(show)

    def ShowListBoxControl(self,show):
        self.valueList.Show(show)
        if self.buttonFlags & wxPROP_DYNAMIC_VALUE_FIELD:
            if show:
                self.middleSizer.Prepend(self.valueList,0,\
                         wx.TOP|wx.LEFT|wx.RIGHT|wx.EXPAND,3)
            else:
                self.middleSizer.Remove(0)
                
            self.Layout()

    def ShowView(self):
        self.UpdatePropertyList()
        self.Layout()

    def EnableCheck(show):
        self.confirmButton.Enable(show)

    def EnableCross(show):
        self.cancelButton.Enable(show)

    def OnClose(self,event):
        self.OnCheck(event)
        self.Destroy()
        return True
    
    def OnOk(self,event):
        if self.modified:
            # Todo: update values
            pass
    
    def OnCross(self,event):
        self.UpdatePropertyList(self.element,self.design)

    def OnSelectProperty(self,event):
        if self.element and self.dictionary:
            index = self.propertyScrollingList.GetSelection()
            key = self.propertyScrollingList.GetClientData(index)
            value = self.element.attributes.get(key,'')
            self.valueText.SetValue(value)
        else:
            self.valueText.SetValue('')
            
        self.valueText.Enable(self.design)
        self.okButton.Enable(self.design)
        self.cancelButton.Enable(self.design)
                    
    def MakeNameValueString(self,name,value):
        padWidth = 12 - len(name)
        if padWidth < 0:
            padWidth = 0
        
        strval = name + (' ' * padWidth) + value
        return strval

    def UpdatePropertyList(self,element,design=0):
        self.propertyScrollingList.Clear()
        self.valueList.Clear()
        self.valueText.SetValue('')

        self.element = element
        self.properties = []
        self.design = design
        self.modified = 0
        self.okButton.Enable(0)
        self.cancelButton.Enable(0)
        
        if self.element and self.dictionary:
            # Get the metadata for this element
            #metadata = self.dictionary.get(element.name,None)
            #if not metadata:
                #metadata = self.dictionary.get('widget',None)
            #if metadata:
                #for child in metadata.getElements():
                    #for property in child.getElements():
                        #name = property.getAttribute('caption','')
                        #if name:
                            #self.properties.append(property)
                            #value = element.attributes.get(name,'')
                            #strval = self.MakeNameValueString(name,value)
                            #self.propertyScrollingList.Append(strval,property)
                            
            for key in element.attributes.keys():
               value = element.attributes.get(key)
               strval = self.MakeNameValueString(key,value)
               self.propertyScrollingList.Append(strval,key)

class PatchEditBook(wx.Notebook):
    'The patch editor'
    def __init__(self,parent,id,instrument,patch):
        'PatchEditPane constructor'
        wx.Notebook.__init__(self,parent,id)
        self.instrument = instrument
        self.patch = patch
        self.nbsizer = wx.Notebook.Sizer

        wx.EVT_NOTEBOOK_PAGE_CHANGED(self,self.GetId(),self.OnPageChanged)
        EVT_DATA_CHANGED(self,self.OnDataChanged)
        
    def OnDataChanged(self,event):
        source = event.source
        dest = event.dest
        try:
            dest.RefreshValue(source)
        except:
            pass
        
    def OnPageChanged(self,event):
        'Placemarker in case we decide to implement a lazy page constructor'
        index = event.GetSelection()
        tab = self.GetPage(index)

        # Load the widgets
        wx.BeginBusyCursor()
        tab.Load()
        wx.EndBusyCursor()
        
        event.Skip()
        
    def AddTab(self,env,element):
        'Add a tab to the notebook and populate the tab'
        caption = element.getCaption()
        tab = PatchEditTab(self,env,self.instrument,self.patch,element)
        wx.Notebook.AddPage(self,tab,caption)
        return tab

    def AddListTab(self,env,element):
        'Add a tab to the notebook and populate the tab'
        caption = element.getCaption()
        tab = ListEditTab(self,env,element)
        wx.Notebook.AddPage(self,tab,caption)
        return tab

    def DeleteAllTabs(self):
        'Delete all tabs'
        self.DeleteAllPages()
        
class PatchEditTab(WidgetBase,wx.Panel):
    'A patch editor tab'
    def __init__(self,parent,env,instrument,patch,element):
        'PatchEditTab constructor'
        # Initialize attributes
        self.instrument = instrument
        self.panel = None
        self.reset = 0
        
        # Initialize the base class
        WidgetBase.__init__(self,env,element,patch,0)
        wx.Panel.__init__(self,parent,-1)
        
        wx.EVT_SIZE(self,self.OnSize)
        
    def Load(self):
        'Load and show the editor'
        # Nothing to do if the editor already exists
        modeId = self.getAttribute('mode','')
        if not self.panel or modeId:
            if self.panel:
                self.panel.Destroy()
                
            url = self.getAttribute('url','')
            self.panel = PatchEditHtmlPage(self,self.env,self.instrument,\
                                           self.patch,url)
            self.panel.Load(self.env,self.patch,modeId,self.reset)
            self.reset = 0
            
        # Set the widgets to the correct enabled state
        self.Enable()
        
    def OnSize(self,event):
        if self.panel:
            self.panel.SetSize(self.GetClientSize())

    def Enable(self,flag=True):
        flag = self.CheckEnable()
        self.panel.Enable(flag)

    def RefreshValue(self,source,flag=True):
        # Similar to Enable() but refreshes values
        if not self.reset:
            reset = self.getAttribute('reset','')
            if reset == 'true':
                # If reset="true" for this tab, then wait to refresh
                # because a new dynamic page will be created the
                # next time the user clicks on this tab. 
                self.reset = 1
            else:                
                flag = self.CheckEnable(flag)
                self.panel.Enable(self,flag)
                if self.panel.group:
                    self.panel.group.RefreshValue(source,flag)

class PatchEditHtmlPage(wx.html.HtmlWindow):
    'A patch editor tab'
    def __init__(self,parent,env,instrument,patch,url):
        'PatchEditTab constructor'
        # Initialize attributes
        self.instrument = instrument
        self.url = url
        
        # This is looked up by the wxHtmlParser and passed to widgets
        self.reset = 0
        
        # Initialize the base classes
        wx.html.HtmlWindow.__init__(self,parent,-1)
        self.SetSize(parent.GetClientSize())
        
        # Initialize attributes
        self.env = env
        self.patch = patch
        self.group = None
        
    def Load(self,env,patch,modeId,reset):
        'Load and show the editor'
        print("env: {}, patch: {}, modeId: {}, reset: {}".format(env, patch, modeId, reset))
        self.reset = reset
        
        # Check for dynamic content. This is a little more complicated 
        # than I'd like it to be, but at least it's confined to this
        # one section of code. This is everything needed to select the 
        # correct patch and html editor. This is used only 
        # when you don't know which editor to use until runtime.
        url = self.url
        if modeId:
            mode = self.instrument.GetInterfaceInfo(modeId)
            if mode:
                # First param contains the patch offset
                parent = self.GetParent()
                param = parent.params[0]
                offset = param.getData()
                
                # Make a reference to the original array but with the offset
                self.patch = Patch(offset)
                self.patch.data = patch.data
    
                # Get the patch id
                patchId = parent.getCurrentVal()
                
                # Get the patch info
                found = 0
                for page in mode.getElements('page'):
                    for tab in page.getElements('tab'):
                        if patchId == tab.getAttribute('patch',''):
                            found = 1
                            break
                    if found:
                        break
                
                if not tab:
                    ShowMessage(self,'Patch definition "%s" not found')
                    return
                
                # Get the url of the html page
                self.url = tab.getAttribute('url')

                # Derive a new environment
                self.env = SynthEnv()
                # Make a shallow copy of the attributes because
                # this tab will overwrite some entries
                self.env.attributes = env.attributes.copy()
                # Use the same map because we want widgets in the 
                # dynamic tab to be able to listen and be notified 
                # of data changes from the main env
                self.env.map = env.map
                self.env.eventHandler = env.eventHandler
                self.env.property = env.property
                self.env.instrument = env.instrument
                self.env.initialized = 1
                
                # Get the params for this patch
                patchId = tab.getAttribute('patch')
                print("patchId: " + patchId)
                patchInfo = self.instrument.GetPatchInfo(patchId)
                
                # Create new copies of the params for this patch
                # The new params will use the new env and patch
                for param in patchInfo.getElements():
                    newParam = Param(self.env,param,self.patch)
                    # Update the dictionary with the new params
                    key = newParam.getId()
                    self.env.attributes.update({key:newParam})
                
        # Get the URL of the HTML file to process
        if not os.path.isfile(url):
            dir = os.path.dirname(self.instrument.path)
            url = os.path.normpath(os.path.join(dir,self.url))

        self.group = GroupWidget(self,self.env,EMPTY_ELEMENT,self.patch)
            
        # Load the html page
        self.LoadPage(url)

        # The reset flag was passed to Widget(). If it was set
        # then the widgets initialized their params, so we can
        # reset this flag
        self.reset = 0
        
    def Enable(self,flag=True):
        # It would be nice to enable/disable the tab handle itself
        # but I don't know how to do that so I enable or disable 
        # all children.
        wx.html.HtmlWindow.Enable(self,flag)
        if self.group:
            self.group.Enable(flag)
        
    def RefreshValue(self,source,flag=True):
        # Similar to Enable() but refreshes values
        wx.html.HtmlWindow.Enable(self,flag)
        if self.group:
            self.group.RefreshValue(source,flag)
     
class ListEditTab(wx.ScrolledWindow):
    'Edits a list in design mode'
    def __init__(self,parent,env,element):
        'PatchEditTab constructor'
        # Initialize attributes
        self.env = env
        self.element = element
        
        # Initialize the base class
        wx.ScrolledWindow.__init__(self,parent,-1)
        self.elb = gizmos.wxEditableListBox(self, -1, element.getCaption(),\
                                     (50,50), (250, 250))

        strings = element.getList()
        self.elb.SetStrings(strings)
      
def ShowMessage(parent,message,style=wx.OK):
    'Display a message box'
    dlg = wx.MessageDialog(parent,message,appname,style)
    intval = dlg.ShowModal()
    dlg.Destroy()
    return intval

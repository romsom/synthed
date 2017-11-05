#-----------------------------------------------------------------------------
# Name:        parameter.py
# Purpose:     synth parameter editing
#
# Author:      John Bair
#              jbair@synthed.org
#
# Created:     2002/08/13
# RCS-ID:      $Id: parameter.py,v 1.16 2002/09/21 07:59:06 fumphco Exp $
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
This module contains parameter widgets and base classes to manage parameter values.

Todo:
    KnobParam:
        Should add a rotator knob widget

    TextParam:
        Isn't fully functional yet.
        Need to add validator for constraints like max length, prohibit non-printable chars?

    Tooltips:
        Should add tooltips and help url to <parameter> element and implement it in the UI
"""

import array,imp,sys,traceback
import wxPython.wx as wx
import wxPython.html as html

from xml2obj import *
from instrument import *

# Some constants for sizer styles
SIZER_FORMAT = wx.wxALL|wx.wxALIGN_CENTER_VERTICAL
SIZER_ALIGN_RIGHT = SIZER_FORMAT|wx.wxALIGN_TOP|wx.wxALIGN_RIGHT|wx.wxADJUST_MINSIZE
SIZER_ALIGN_LEFT = SIZER_FORMAT|wx.wxALIGN_TOP|wx.wxALIGN_LEFT|wx.wxADJUST_MINSIZE

# wxMSW GetCharWidth() returns too small a value
CHAR_WIDTH_PAD = 2

# Utility functions
def AddVariable(dictionary,object):
    'Add object to a dictionary if there is an id'
    try:
        key = object.getId()
        if key:
            dictionary.update({key:object})
    except:
        pass
        
def CreateLabel(parent,group,element):
    'Create a label and insert left-aligned into the group'
    caption = element.getAttribute('caption','') + ':'
    label = wx.wxStaticText(parent,-1,caption)
    if group:
        group.AddWindow(label,0,SIZER_ALIGN_LEFT,5)
    return label

def FormatVal(format,val):
    'Convert a value to a string using a format string'
    if format:
        strval = format % (val)
    else:
        strval = str(val)
    return strval
        
def ShowError(parent,style=wx.wxOK):
    'Display an exception and traceback in a message box'
    message = ''
    TBStrings = traceback.format_exception(*sys.exc_info())
    for line in TBStrings:
        message += (line)
    dlg = wx.wxMessageDialog(parent,message,'SynthEd',style)
    intval = dlg.ShowModal()
    dlg.Destroy()
    return intval

def TwosComplement(intdata):
    'Extend the high bit of a twos complement value to make a native int'
    # Get the high bit
    for i in range(0,32):
        if intdata & (1 << i):
            bitlen = i + 1
            
    # Extend the high bit
    if intdata & (1 << (bitlen - 1)):
        for i in range(bitlen,32):
            intdata |= (1 << i)
    return intdata

# EVT_DATA_CHANGED is used to notify widgets of data value changes
wxEVT_DATA_CHANGED = wx.wxNewEventType()

def EVT_DATA_CHANGED(win,func):
    win.Connect(-1,-1,wxEVT_DATA_CHANGED,func)

class DataChangedEvent(wx.wxPyEvent):
    def __init__(self,source,dest):
        wx.wxPyEvent.__init__(self)
        self.SetEventType(wxEVT_DATA_CHANGED)
        self.source = source
        self.dest = dest

class SynthEnv:
    'Editor environment attributes'
    def __init__(self):
        'SynthEnv constructor'
        # A dictionary of attributes for the local namespace 
        # for runtime expression evaluation
        self.attributes = {}
        
        # A param:widget dependency map
        # The key is the id of the parameter
        # The value is a list of widgets that use the parameter 
        # {'a':[widget1,widget2],'b':[widget1,widget3],...}
        # When a parameter is modiifed, it checks to see if there 
        # are any other widgets that are using this parameter, 
        # and if so, it notifies them that the value may have changed.
        self.map = {}
        
        # Widget notification occurs only after all widgets and 
        # the map has been initialized
        self.initialized = 0
        
        # The window that will receive and process EVT_DATA_CHANGED
        self.eventHandler = None
        
        # Reference to property editor
        self.property = None
        
        # The instrument
        self.instrument = None

    def Clear(self):
        'The dependency map must be cleared when changing pages'
        # Clear the dependency map because the widget references
        # are no longer valid
        self.map.clear()
        self.initialized = 0
        self.eventHandler = None
                                
class ValueList(Element):
    """A Value list is a list of nested lists and item values.
       This corresponds to the <list> entity in "decoder.dtd".
    """
    def __init__(self,name,attributes,children):
        'ValueList constructor'
        Element.__init__(self,name,attributes,children)
        
        self._list = children
        self._cached = 0
        self._maxChars = 3
        
    def _getList(self,refnode):
        'Convert the <list> element into a sequence (recursive)'
        items = []
        try:
            for child in refnode.getElements():
                if child.name == 'list':
                    # The item is a list so get the list
                    item = self._getList(child)
                elif child.name == 'item':
                    # The item is a value
                    item = child.getAttribute('value')
                    self._maxChars = max(self._maxChars,len(item))
                # Append the item
                items.append(item)
        except:
            pass
        return items
    
    def getList(self):
        'Get the list'
        # Only build the list the first time
        if self._cached == 0:
            # Convert the <list> element into a sequence
            self._list = self._getList(self)
            self._cached = 1
        return self._list

    def getData(self,strval):
        # Find a value in the list
        intval = int(strval)
        
        items = self.getList()
        for i in range(0,len(items)):
            testval = items[i]
            if strval.lower() == testval.lower():
                intval = i
        
        return intval
    
    def getMaxChars(self):
        'Return the max number of chars in the longest item'
        items = self.getList()
        return self._maxChars
    
class ValueScale(Element):
    """Computes display values using a scale (a set of stepped ranges).
       This corresponds to the <scale> entity in "decoder.dtd".
    """
    def __init__(self,name,attributes,children):
        'ValueScale constructor'
        Element.__init__(self,name,attributes,children)
        
        # Get scale min and max
        self.min = int(self.EvalAttribute('min'))
        self.max = int(self.EvalAttribute('max'))
        
    def _getIncrement(self,element):
        'The "increment" attribute'
        # Any legal python numeric expression is permitted
        return element.EvalAttribute('increment','0')

    def _getMinVal(self,element):
        'The "minval" attribute'
        (mindata,maxdata) = self._getRange(element)
        strval = element.getAttribute('minval','')
        if strval:
            try:
                # Any legal python numeric expression is permitted
                numval = eval(strval)
            except:
                # It's an arbitrary string value
                return strval
        else:
            # Failsafe
            numval = mindata
            if numval > self.max:
                numval = TwosComplement(numval)
            
        return numval

    def _getRange(self,element):
        'Get the "mindata" and "maxdata" attributes'
        mindata = int(element.EvalAttribute('min','0'))
        maxdata = int(element.EvalAttribute('max','0'))
        if mindata > self.max:
            mindata = TwosComplement(mindata)
        if maxdata > self.max:
            maxdata = TwosComplement(maxdata)
        return (mindata,maxdata)
    
    def getVal(self,intdata,format=''):
        'Get the display (external) value for a data (internal) value'
        for child in self.children:
            # Get increment, mindata and maxdata
            increment = self._getIncrement(child)
            (mindata,maxdata) = self._getRange(child)
            
            # If increment == 0 then <range> contains a special value
            if increment == 0 and intdata == mindata:
                # It's a string constant
                strval = self._getMinVal(child)
                break
            else:
                # Check if it's between the range min and max
                if mindata <= intdata <= maxdata:
                    minval = self._getMinVal(child)
                    # Compute the value using minval and increment
                    intval = minval + (increment * (intdata - mindata))
                    # Check if the <range> element specifies a format
                    format = child.getAttribute('format')
                    if not format:
                        # See if the <scale> element specifies a format
                        format = self.getAttribute('format','')
                    # Format the value
                    strval = FormatVal(format,intval)
                    break    
        else:
            # A value was not found - this should not happen
            strval = 'Bad scale value %d in %s' % (intdata,self.getCaption())
            raise(strval.encode())
        
        return strval
    
    def getData(self,strval):
        'Get the data (internal) value for a display (external) value'
        for child in self.element.children:
            # Get increment, mindata and maxdata
            increment = self._getIncrement(child)
            (mindata,maxdata) = self._getMinMaxData(child)
            minval = self._getMinVal(child)
            
            # If increment == 0 then <range> contains a special value
            if increment == 0 and strval.lower() == minval.lower():
                # It's a string constant
                intdata = mindata
                break
            else:
                # Check if strval matches any of the display values 
                # between the range min and max. Unfortunately, I 
                # step through all valid values in the range, compute 
                # the display (external) value for each data (internal) 
                # value and check if the passed strval matches.
                # Not the most efficient algorithm, but this is 
                # only used when a user manually enters a value into 
                # a text box and it's the only way I could think of 
                # to validate the entry
                for dataval in range(mindata,maxdata+1):
                    try:
                        testval = \
                           str(minval + (increment * (dataval - mindata)))
                        if int(strval) == int(testval) or \
                           float(strval) == float(testval):
                            intdata = dataval
                            break
                    except:
                        pass
        return intdata
    
    def getList(self):
        items = []
        i = self.min
        while i <= self.max:
            try:
                value = self.getVal(i)
            except:
                value = ''
            items.append(value)
            i +=1
            
        return items
    
    def getMaxChars(self):
        maxlen = 3
        for child in self.children:
            # Get increment, mindata and maxdata
            increment = self._getIncrement(child)
            (mindata,maxdata) = self._getRange(child)
            
            # If increment == 0 then <range> contains a special value
            if increment == 0:
                # It's a string constant
                strval = self._getMinVal(child)
                maxlen = max(maxlen,len(strval))
            else:
                # Get size of minval
                intdata = mindata
                minval = self._getMinVal(child)
                # Compute the value using minval and increment
                numval = minval + (increment * (intdata - mindata))
                # Check if the <range> element specifies a format
                format = child.getAttribute('format')
                if not format:
                    # See if the <scale> element specifies a format
                    format = self.getAttribute('format','')
                # Format the value
                strval = FormatVal(format,numval)
                maxlen = max(maxlen,len(strval))
                # Get size of maxval
                intdata = maxdata
                # Compute the value using minval and increment
                numval = minval + (increment * (intdata - mindata))
                # Check if the <range> element specifies a format
                format = child.getAttribute('format')
                if not format:
                    # See if the <scale> element specifies a format
                    format = self.getAttribute('format','')
                # Format the value
                strval = FormatVal(format,numval)
                maxlen = max(maxlen,len(strval))
                             
        return maxlen
            
class ParamByte(Element):
    """Sysex parameter values are packed into bytes, possibly  
       across byte boundaries. A Param references one or more ParamBytes.
       Each ParamByte holds a contiguous range of bits in a byte.
       This corresponds to the <byte> entity in "patch.dtd".
    """
    def __init__(self,element=EMPTY_ELEMENT,patch=None):
        'ValueByte constructor'
        Element.__init__(self,element.name,element.attributes,element.children)
        self._patch = patch
        # Construct dummy data and offset if none is specified
        # This can happen when a widget manages a value that is not 
        # in the data block. For example, a real-time control may 
        # send MIDI messages but the value may not be saved with the patch.
        # The dummy byte holds the current value and will be discarded 
        # when the widget is destroyed.
        if self._patch == None:
            self._patch = Patch()
            self._patch.fromstring('\x00')
            self._offset = 0
            self._bitstart = 0
            self._bitstop = 7
            self._temporary = 1
        else:
            # Get byte offset - any python numeric expression permitted
            self._offset = int(self.EvalAttribute('offset','0'))
            # Get bitstart - any python numeric expression permitted
            self._bitstart = int(self.EvalAttribute('bitstart','0'))
            # Get bitstop - any python numeric expression permitted
            self._bitstop = int(self.getAttribute('bitstop','7'))
            self._temporary = 0
            
        # Compute bitmask from bitstart to bitstop inclusive
        self._bitmask = 0
        for i in range(self._bitstart,self._bitstop+1):
            bit = 1 << i
            self._bitmask += bit
                                
    def getBitLen(self):
        'Bit length'
        return self._bitstop - self._bitstart + 1
    
    def getBitstart(self):
        'Start bit'
        return self._bitstart
    
    def getBitstop(self):
        'Stop bit'
        return self._bitstop
    
    def getData(self):
        'Get current value'
        # Perform a bitwise "and" with the bitmask
        intdata = self._patch.get(self._offset) & self._bitmask
        # Right-shift by bitstart so that the value is returned 
        # as if it were right-aligned to bit 0
        intdata = intdata >> self._bitstart
        return intdata
    
    def setData(self,intdata):
        'Set new value'
        # Set the new value
        intdata = intdata << self._bitstart
        self._patch.set(self._offset, \
            (self._patch.get(self._offset) & (~self._bitmask)) | \
            (intdata & self._bitmask))
        
class Param(Element):
    """A parameter represents a single value from a sysex data dump.
       This corresponds to the <parameter> entity in "patch.dtd".
    """
    def __init__(self,env,element=EMPTY_ELEMENT,patch=None):
        'Param constructor'
        # Initialize attributes
        self.env = env
        # The patch data dump
        self.patch = patch
        # The array of ParamBytes
        self.bytes = []
        
        # Construct base class
        Element.__init__(self,element.name,element.attributes,element.children)
        
        # Sysex parameter values are packed into bytes, possibly  
        # across byte boundaries.
        # A Param references one or more ParamBytes.
        # Each ParamByte holds a contiguous range of bits in a byte
        
        # If a patch is passed then process all <byte> or <array> elements
        if element and patch:
            for child in self.getElements():
                if child.name == 'byte':
                    # Get the <byte> element
                    byte = ParamByte(child,patch)
                    # Append it to the bytes list
                    self.bytes.append(byte)
                elif child.name == 'array':
                    offset = int(child.EvalAttribute('offset'))
                    length = int(child.EvalAttribute('length'))
                    for i in range(length):
                        # Create a <byte> element
                        attributes = {'offset':str(offset+i)}
                        # Even though we are creating a <byte> element
                        # we leave the name='array' so that we can
                        # recombine the individual byte elements into 
                        # a single array element when generating XML
                        newElement = Element('array',attributes,[])
                        byte = ParamByte(newElement,patch)
                        # Append it to the bytes list
                        self.bytes.append(byte)
                    
        # If there are still no <byte> elements then construct a dummy one
        # for temporary storage of data.
        if len(self.bytes) == 0:
            byte = ParamByte()
            self.bytes.append(byte)
            # Initialize the data in case this is a param constant
            self.initData(None)
            
    def __del__(self):
        'Param destructor'
        # Unregister from the parameter map
        self.Unregister()
            
        # Remove the reference to self in the attribute dictionary
        key = self.getId()
        if key:
            del self.env.attributes[key]
            #delattr(self.env.module,key)
        
    def Register(self,listener):
        'Maintain a 1:N map of parameters to listeners'
        # See the explanation for SynthEnv.map parameter map
        if listener:
            key = self.getId()
            listeners = self.env.map.get(key)
            if listeners:
                # If not already in the list
                if listener not in listeners:
                    # Add the parent param to the list
                    listeners.append(listener)
            else:
                # Create a new param list
                listeners = [listener]
                # Insert the {key:value} pair into the byte map
                self.env.map.update({key:listeners})
    
    def Unregister(self,listener=None):
        'Remove this from the 1:N map of parameters to listeners'
        # See the explanation for SynthEnv.map parameter map
        # Lookup the registration
        key = self.getId()
        listeners = self.env.map.get(key)
        if listeners:
            if listener:
                # Unregister the listener
                try:
                    listeners.remove(listener)
                    if len(listeners) < 1:
                        del self.env.map[key]
                except:
                    pass
            else:
                # Delete the registry entry
                del self.env.map[key]
    
    def _NotifyListeners(self,source):
        'Notify listeners that the parameter value may have changed'
        # See the explanation for SynthEnv.map parameter map
        # Skip if the map has not yet been initialized
        # Skip if there's no data block
        # Skip if there's no source
        if self.env.initialized and self.patch and source:
            # Start with an empty list of listeners to notify
            listenerArray = []
            # Get the listeners list for this parameter
            key = self.getId()
            listeners = self.env.map.get(key)
            if listeners:
                # Iterate over all listeners in the list
                for listener in listeners:
                    # Don't notify source (prevent infinite recursion :-)
                    if listener is not source:
                        # Add the listener to the notification list
                        # preventing duplicates
                        if listener not in listenerArray:
                            listenerArray.append(listener)
                                    
            # Notify the affected listeners - this is done by posting
            # events to the patch edit pane, which in turn will call 
            # widget.RefreshValues(). wxPostEvent queues the events 
            # and returns immediately; the other widgets will be 
            # asynchronously updated.
            for listener in listenerArray:
                event = DataChangedEvent(source,listener)
                wx.wxPostEvent(self.env.eventHandler,event)
        
    def getBitLen(self):
        'The bit length is the sum of bits used over all referenced bytes'
        count = 0
        for byte in self.bytes:
            count += byte.getBitLen()
        return count
    
    def getData(self):
        'Join pieces from the param bytes to get the value'
        intdata = 0
        bitlen = 0
        
        # We assume that bytes are in MSB order.
        bytes = self.bytes
        for i in range(len(bytes),0,-1):
            # Get the next most significant byte
            byte = bytes[i-1]
            # Left-shift the value and bitwise "or" with accumlator
            intdata |= byte.getData() << bitlen
            # Keep track of how many bits we have used
            bitlen += byte.getBitLen()
            
        # Handle a variable length two's complement format
        maxdata = self.getMax()
        
        # If the value > maxdata, it must be a two's complement number
        if intdata > maxdata:
            intdata = TwosComplement(intdata)
            
        return intdata

    def setData(self,source,intdata):
        'Split the value and store the component bytes/bits'
        # mindata <= intdata <= maxdata
        intdata = min(intdata,self.getMax())
        intdata = max(intdata,self.getMin())

        # Validate the value
        flag = self._validate(intdata)
        if not flag:
            return

        #Slice the value and stuff the pieces into the param bytes
        bitdata = 0
        bitstart = 0
        bitstop = 0
        # We assume that bytes are in MSB order
        bytes = self.bytes
        for i in range(len(bytes),0,-1):
            # Get the next most significant byte
            byte = bytes[i-1]
            # Compute the bitmask to bitwise "and" with the value
            bitmask = 0
            bitstop = bitstart + byte.getBitLen()
            for i in range(bitstart,bitstop):
                bitmask |= 1 << i
            # Bitwise "and" the bitmask with the value
            # and right-shift as if it were right-aligned with bit 0
            bitdata = (intdata & bitmask) >> bitstart
            # Set the bits
            byte.setData(bitdata)
            # Advance the bitmask start
            bitstart = bitstop

        # Notify the instrument of the parameter change
        if self.env.initialized and source:
            self.env.instrument.ParameterChange(self)
        
        # Notify any other affected widgets that the value may have changed
        self._NotifyListeners(source)
    
    def initData(self,source):
        # Initialize the data
        min = self.getMin()
        max = self.getMax()
        if min == max:
            self.setData(source,min)
        else:
            init = int(self.EvalAttribute('init','0'))
            if init:
                self.setData(source,init)
            else:
                self.setData(source,0)

    def getMax(self):
        'The maximum data (internal) value'
        # Any legal numeric python expression is permitted
        intdata = int(self.EvalAttribute('max','0'))
        return intdata
    
    def getMin(self):
        'The minimum data (internal) value'
        # Any legal numeric python expression is permitted
        intdata = int(self.EvalAttribute('min','0'))

        # Handle a variable length two's complement format
        # If the high bit is set, extend it
        maxdata = self.getMax()
        if intdata > maxdata:
            intdata = TwosComplement(intdata)
        return intdata
        
    def getStrVal(self):
        'Get a string parameter value'
        # This is for character or string parameter values
        # like patch names or category names.
        strval = ''
        for byte in self.bytes:
            intdata = byte.getData()
            if intdata > 0:
                strval += chr(intdata)
            else:
                break
        return strval
    
    def setStrVal(self,source,strval,pad):
        # This is for character or string parameter values
        # like patch names or category names. The value will 
        # be right-padded if the passed strval is 
        # shorter than the parameter value.
        i = 0
        for byte in self.bytes:
            if i < len(strdata):
                byte.setData(ord(strdata[i]))
            else:
                byte.setData(pad)
            i += 1

        # Notify any other affected widgets that the value may have changed
        self._NotifyListeners(source)
            
    def _validate(self,intval):
        'Value must be validated before it is stored'
        flag = 1
        expr = self.getAttribute('validate','')
        if expr:
            # The special variable _value holds the new value
            self.env.attributes.update({'_value':intval})

            # Any valid python boolean expression is permitted
            flag = eval(expr,globals(),self.env.attributes)
            
            del self.env.attributes['_value']
            #flag = eval(expr,globals(),vars(self.env.module))
        return flag
                    
class WidgetParam(Element):
    """A wrapper around a Param with some additional UI attributes.
       This corresponds to the <parameter> entity in interface.dtd
    """
    def __init__(self,env,parent,element=EMPTY_ELEMENT):
        # Initialize attributes
        self.env = env
        self.parent = parent
        
        # Construct base class
        Element.__init__(self,element.name,element.attributes,element.children)

        # Get the id of the parameter to wrap
        id = self.getId()
        if id:
            # Get the referenced param
            self.param = self.env.attributes.get(id)
            if not self.param:
                str = 'Reference to non-existent parameter %s' % id
                raise(str.encode())
        else:
            # Make a dummy param to hold temporary values
            self.param = Param(env)

        # Register parent to listen to param
        self.param.Register(self.parent)

    def getData(self):
        return self.param.getData()
    
    def initData(self,source):
        return self.param.initData(source)
    
    def setData(self,source,value):
        return self.param.setData(source,value)
    
    def getMaxChars(self):
        return self.param.getMaxChars()
    
    def getMax(self):
        return self.param.getMax()
        
    def getMin(self):
        return self.param.getMin()
        
    def getIndexer(self):
        'Check if this value is a list index'
        # If the indexer attribute is true (the default), 
        # the value is an index into a ValueList
        indexer = self.getAttribute('indexer','true')
        if indexer == 'true':
            return 1
        else:
            return 0
        
    def getStrVal(self):
        return self.param.getStrVal()
        
    def setStrVal(self,source,value):
        pad = ord(self.getAttribute('pad','\x00'))
        return self.param.setStrVal(source,value,pad)

class WidgetBase(Element):
    'Base widget class that connects the widget to the associated params'
    def __init__(self,env,element,patch,init):
        'WidgetBase constructor'
        # Initialize attributes
        self.env = env
        self.patch = patch
        self.params = []
        self.widgetCell = None
        
        # Construct base class
        Element.__init__(self,element.name,element.attributes,element.children)

        # Load parameters
        for param in self.getElements('parameter'):
            widgetParam = WidgetParam(env,self,param)
            self.params.append(widgetParam)
        
        if len(self.params) < 1:
            # Make a dummy param to hold temporary values
            widgetParam = WidgetParam(env,self)
            self.params.append(widgetParam)
            
        if init:
            self.initData()
            
    def getData(self):
        'Get the data (internal) value for this widget'
        key = self.getDecoder()
        if key:
            decoder = self.env.attributes.get(key,None)
        else:
            decoder = None
            
        if key and decoder == None:
            # user defined decoder
            #module = self.env.attributes.get(self.env.moduleName)
            classref = getattr(self.env.instrument.module,key)
            instance = classref(self)
            intdata = instance.getData()
        else:
            # The actual data value for the widget is stored in the 
            # last parameter in the list. Earlier parameters in the list are 
            # used to receive notifications when other widgets change 
            # values that this widget cares about, or to index into 
            # nested lists. This is probably not the best way to do this,
            # because this assumption is not explicit in the XML DTD.
            param = self.params[-1]
            intdata = param.getData()
        return intdata
    
    def setData(self,source,intdata):
        'Set the data(internal) value for this widget'
        # mindata <= intdata <= maxdata
        intdata = min(intdata,self.getMax())
        intdata = max(intdata,self.getMin())

        key = self.getDecoder()
        if key:
            decoder = self.env.attributes.get(key,None)
        else:
            decoder = None
            
        if key and decoder == None:
            # user defined decoder
            #module = self.env.attributes.get(self.env.moduleName)
            classref = getattr(self.env.instrument.module,key)
            instance = classref(self)
            instance.setData(source,intdata)
        else:
            # Assumes that the actual data value for the parameter is 
            # the last value in the list. See getData() for more info.
            param = self.params[-1]
            param.setData(source,intdata)
            
    def initData(self):
        key = self.getDecoder()
        if key:
            decoder = self.env.attributes.get(key,None)
        else:
            decoder = None
            
        if key and decoder == None:
            # user defined decoder
            #module = self.env.attributes.get(self.env.moduleName)
            classref = getattr(self.env.instrument.module,key)
            instance = classref(self)
            instance.initData(self)
        else:
            # Assumes that the actual data value for the parameter is 
            # the last value in the list. See getData() for more info.
            param = self.params[-1]
            param.initData(self)
                    
    def getDataFromVal(self,strval):
        'Get a corresponding data value from a display value'
        # Not the best, but it's only used when the user manually 
        # enters a display (external) value, in which case you need 
        # to convert it into a data (internal) value to update the 
        # parameter value.
        key = self.getDecoder()
        if key:
            decoder = self.env.attributes.get(key,None)
        else:
            decoder = None
            
        if decoder:
            # Find the value using the decoder
            intval = decoder.getData(strval)
        else:
            # No decoder
            intval = int(strval)
        return intval
            
    def getCurrentVal(self):
        'Get the current display value'
        param = self.params[-1]
        # Get the id of the parameter to wrap
        id = param.getId()
        if id:
            # Get the referenced param
            param = self.env.attributes.get(id)
        type = param.getAttribute('type','')
        if type in ('id','str'):
            return param.getStrVal()
        else:
            intdata = self.getData()
            return self.getVal(intdata)
        
    def getDecoder(self):
        'Id of the element used by the decoder to convert '
        'between data (internal) and display (external) values'
        return self.getAttribute('decoder','')
    
    def getEnable(self):
        'An expression that controls the enable state of the widget'
        return self.getAttribute('enable','')
    
    def getFormat(self):
        'The display format'
        return self.getAttribute('format','')
    
    def getList(self):
        'Get the list of possible values for the widget'
        items = []
        
        key = self.getDecoder()
        if key:
           decoder = self.env.attributes.get(key,None)
           if decoder:
               #valueList = getattr(self.env.module,key)
               items = decoder.getList()
               # We want the list - not the item
               # That's why len(params) - 1
               for i in range(0,len(self.params)-1):
                   param = self.params[i]
                   if param.getIndexer():
                       intdata = param.getData()
                       if 0 <= intdata < len(items):
                           items = items[intdata]
                       else:
                           strval = 'Bad index %d in %s on %s' % \
                            (intdata,decoder.getCaption(),self.getCaption())
                           raise(strval.encode())
           else:
               #module = self.env.attributes.get(self.env.moduleName)
               classref = getattr(self.env.instrument.module,key)
               instance = classref(self)
               items = instance.getList()

        return items
        
    def getLayout(self):
        return self.getAttribute('layout','')
    
    def getMaxChars(self):
        'Guess the maximum number of characters that this param will display'
        maxChars = 3
        
        key = self.getDecoder()
        if key:
            decoder = self.env.attributes.get(key)
        else:
            decoder = None
            
        if decoder and hasattr(decoder,'getMaxChars'):
            #valueList = getattr(self.env.module,key)
            maxChars = decoder.getMaxChars()
        else:
            # Get min and max values
            mindata = self.getMin()
            maxdata = self.getMax()
            minval = self.getVal(mindata)
            maxval = self.getVal(maxdata)
            value = self.getCurrentVal()
            # Get the max length of min val, current val and max val
            maxChars = max(len(value),max(len(minval),len(maxval))) + 1
        
        return maxChars
    
    def getMax(self):
        param = self.params[-1]
        return param.getMax()
    
    def getMin(self):
        param = self.params[-1]
        return param.getMin()
    
    def getVal(self,intdata):
        'Get the display value for the given data value'
        strval = ''
        key = self.getDecoder()
        if key:
            decoder = self.env.attributes.get(key,None)
        else:
            decoder = None
            
        if decoder and decoder.name == 'list':
            # Get the value using the referenced list
            # Todo: maybe should just return the intdata?
            items = self.getList()
            try:
                strval = items[intdata]
            except:
                str = 'List index %d out of range on %s' % \
                    (intdata,self.getDecoder())
                raise(str.encode())
        elif decoder and decoder.name == 'scale':
            # Get the value using the referenced scale
            format = self.getFormat()
            strval = decoder.getVal(intdata,format)
        elif key:
            #module = self.env.attributes.get(self.env.moduleName)
            # user defined decoder must return a string value
            classref = getattr(self.env.instrument.module,key)
            instance = classref(self)
            strval = instance.getVal(intdata)
        else:
            # No decoder
            format = self.getFormat()
            strval = FormatVal(format,intdata)
               
        return strval
    
    def CheckEnable(self,flag=1):
        'Decides if this widget should be enabled/disabled'
        if flag:
            expr = self.getEnable()
            if expr:
                # Any valid python boolean expression is permitted
                flag = eval(expr,globals(),self.env.attributes)
                #flag = eval(expr,globals(),vars(self.env.module))
        return flag
                    
    def OnFocus(self,event):
        if self.env.property:
            self.env.property.UpdatePropertyList(self)
        event.Skip()

    def SetTip(self,window):
        strval = self.getAttribute('tip','')
        if strval and hasattr(window,'SetToolTip'):
            tip = wx.wxToolTip(strval)
            window.SetToolTip(tip)
            
    def SetWidgetCell(self,cell):
        self.widgetCell = cell
        
    def Unregister(self):
        for param in self.params:
            param.Unregister()
            
class ButtonWidget(WidgetBase,wx.wxButton):
    'Button widget'
    def __init__(self,parent,env,element,patch,init):
        'CheckWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        # Add the button
        label = self.getCurrentVal()
        wx.wxButton.__init__(self,parent,-1,label)

        # Set tool tip
        self.SetTip(self)
        
        # Event handlers
        wx.EVT_BUTTON(self,self.GetId(),self.OnClick)
        wx.EVT_SET_FOCUS(self,self.OnFocus)
        
    def OnClick(self,event):
        'Clicking the button cycles through the possible values'
        intval = self.getData() + 1
        if intval > self.getMax():
            intval = self.getMin()
        self.setData(self,intval)
        
        label = self.getCurrentVal()
        self.SetLabel(label)
        
        event.Skip()
    
    def Enable(self,flag=wx.true):
        'Enable/disable the button'
        flag = self.CheckEnable(flag)
        wx.wxButton.Enable(self,flag)
        return flag

    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            'Refresh the widget from the data'
            label = self.getCurrentVal()
            self.SetLabel(label)

class CheckWidget(WidgetBase,wx.wxCheckBox):
    'CheckBox widget'
    def __init__(self,parent,env,element,patch,init):
        'CheckWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        # Add the checkbox
        wx.wxCheckBox.__init__(self,parent,-1,'')
        
        self.SetForegroundColour(parent.GetForegroundColour())
        self.SetBackgroundColour(parent.GetBackgroundColour())
        
        # Initialize the value from the data
        intdata = self.getData()
        self.SetValue(intdata)
        
        # Set tool tip
        self.SetTip(self)
                    
        # Event handlers
        wx.EVT_CHECKBOX(self,self.GetId(),self.OnClick)
        wx.EVT_SET_FOCUS(self,self.OnFocus)
        
    def OnClick(self,event):
        'Toggle the checkbox and the underlying data'
        booldata = self.GetValue()
        if booldata:
            intdata = 1
        else:
            intdata = 0
        self.setData(self,intdata)
    
    def Enable(self,flag=wx.true):
        'Enable/disable the CheckBox'
        flag = self.CheckEnable(flag)
        wx.wxCheckBox.Enable(self,flag)
        return flag

    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            'Refresh the widget from the data'
            intdata = self.getData()
            self.SetValue(intdata)

class ChoiceWidget(WidgetBase,wx.wxPanel):
    'Choice widget (Dropdown read-only combo box)'
    def __init__(self,parent,env,element,patch,init):
        'ChoiceWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        # Construct the choice control
        wx.wxPanel.__init__(self,parent,-1,style=wx.wxBORDER_NONE)
        self.sizer = wx.wxBoxSizer(wx.wxHORIZONTAL)
        
        self.combo = wx.wxComboBox(self,-1,\
              style=wx.wxCB_DROPDOWN|wx.wxCB_READONLY)
        self.sizer.Add(self.combo,1,SIZER_FORMAT,0)
        
        # Initialize the value
        self.LoadList()
        intdata = self.getData()
        if 0 <= intdata < self.combo.GetCount():
            self.combo.SetSelection(intdata)
        
        # Adjust the size to fit the list
        size = self.combo.GetBestSize()
        width = size.GetWidth()
        height = size.GetHeight()
        maxChars = self.getMaxChars() + 1
        maxWidth = maxChars * (self.combo.GetCharWidth() + CHAR_WIDTH_PAD)
        width = max(width,maxWidth)
        self.SetSize((width,24))
        self.combo.SetSize((width,24))
        
        self.SetSizerAndFit(self.sizer)
        self.SetAutoLayout(1)

        # Set tool tip
        self.SetTip(self.combo)
        
        # Event handlers
        wx.EVT_COMBOBOX(self.combo,self.combo.GetId(),self.OnChoice)
        wx.EVT_SET_FOCUS(self.combo,self.OnFocus)
        
    def OnChoice(self,event):
        'Set the data value from the selection'
        intdata = self.combo.GetSelection()
        if intdata > -1:
            self.setData(self,intdata)
            # If the new value fails validation, then the 
            # combo box will be out of sync with the parameter value.
            # Unfortunately, attempts to self.SetSelection(self.getData())
            # do not appear to work while the EVT_CHECKBOX is still being
            # handled. So I have no choice but to post a second event
            # to tell the combo box that the value may have changed.
            event = DataChangedEvent(self,self)
            wx.wxPostEvent(self.env.eventHandler,event)
            
    def LoadList(self):
        'Clear and load the list'
        items = self.getList()
        self.combo.Clear()
        for item in items:
            self.combo.Append(item)
            
    def Enable(self,flag=wx.true):
        'Enable/Disable'
        flag = self.CheckEnable(flag)
        wx.wxPanel.Enable(self,flag)
        self.combo.Enable(flag)
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            'Refresh the widget from the data'
            self.LoadList()
            intdata = self.getData()
            self.combo.SetSelection(intdata)
                
class EditWidget(WidgetBase,wx.wxTextCtrl):  
    'Textedit widget'
    def __init__(self,parent,env,element,patch,init):
        'EditWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        self.insertionPoint = 0
        
        # Add the text control
        strval = self.getCurrentVal()
        wx.wxTextCtrl.__init__(self,parent,-1,strval,style=wx.wxTE_PROCESS_ENTER)

        # Set tool tip
        self.SetTip(self)
        
        # Event handlers
        wx.EVT_SET_FOCUS(self,self.OnFocus)
        wx.EVT_TEXT(self,self.GetId(),self.OnText)
        
    def OnText(self,event):
        self.insertionPoint = self.GetInsertionPoint()
        strval = wx.wxTextCtrl.GetValue(self)
        self.SetValue(strval)
        self.SetInsertionPoint(self.insertionPoint)
        
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxTextCtrl.Enable(self,flag)
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        strval = self.getCurrentVal()
        self.SetValue(strval)

class EnvelopeWidget(WidgetBase,wx.wxControl):
    'Envelope widget'
    def __init__(self,parent,env,element,patch,init):
        'EnvelopeWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)

        # Envelope parameters
        self.mouseDown = 0
        self.visibleParams = []
        self.points = []
        self.lastPoint = wx.wxPoint(0,0)
        self.paramIndex = -1
        self.drag = 0
        
        # Construct the list of visible params
        for param in self.params:
            if param.getIndexer():
                self.visibleParams.append(param)
        
        # Compute the best size
        self.width = 513
        self.height = 213
        size = self.GetBestSize()
        self.minWidth = self.width
        
        # Create the panel
        wx.wxControl.__init__(self,parent,-1,wx.wxDefaultPosition,size,style=wx.wxBORDER_NONE)

        # Construct pens and brushes
        self.background = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_WINDOW)
        highlight = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_HIGHLIGHT)
        grey = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_GRAYTEXT)
        self.dashPen = wx.wxPen(grey,1,wx.wxDOT)
        self.bluePen = wx.wxPen(highlight,2)
        self.greyPen = wx.wxPen(grey,2)
        self.blueBrush = wx.wxBrush(highlight,wx.wxSOLID)	
        self.greyBrush = wx.wxBrush(grey,wx.wxSOLID)	
        
        # Event handlers
        wx.EVT_PAINT(self,self.OnPaint)
        wx.EVT_LEFT_DOWN(self,self.OnMouseDown)
        wx.EVT_LEFT_UP(self,self.OnMouseUp)
        wx.EVT_MOTION(self,self.OnMotion)
        wx.EVT_ENTER_WINDOW(self,self.OnEnterWindow)
        # EVT_SET_FOCUS doesn't seem to work here so I put the property
        # viewer activate into EVT_LEFT_DOWN instead
        wx.EVT_SET_FOCUS(self,self.OnFocus)
        wx.EVT_KILL_FOCUS(self,self.OnKillFocus)
        
        # Set tool tip
        self.SetTip(self)
        
        # Change the cursor to indicate that user can move the points
        self.SetCursor(wx.wxStockCursor(wx.wxCURSOR_HAND))
        
    def OnKillFocus(self,event):
        self.mouseDown = 0
        self.lastPoint = wx.wxPoint(0,0)
        self.paramIndex = -1
        event.Skip()
        
    def OnEnterWindow(self,event):
        # If the mouse enters the window while the left mouse button
        # is down, and if it was dragging a handle when it left the 
        # window, then just resume. Otherwise, stop.
        if not event.LeftIsDown():
            self.mouseDown = 0
            self.lastPoint = wx.wxPoint(0,0)
            self.paramIndex = -1
        event.Skip()
        
    def OnMotion(self,event):
        if self.mouseDown == 1:
            point = event.GetPosition()
            self.DoDrag(point)
        else:
            event.Skip()
            
    def OnMouseDown(self,event):
        self.mouseDown = 1
        self.lastPoint = event.GetPosition()
        
        # Remove this next bit if you get the EVT_SET_FOCUS event working
        if self.env.property:
            self.env.property.UpdatePropertyList(self)
        event.Skip()
        
    def OnMouseUp(self,event):
        self.mouseDown = 0
        self.lastPoint = wx.wxPoint(0,0)
        self.paramIndex = -1
        
    def OnPaint(self,event):

        isEnabled = self.IsEnabled()
        if isEnabled:
            self.SetBackgroundColour(self.background)
        else:
            parent = self.GetParent()
            self.SetBackgroundColour(parent.GetBackgroundColour())

        (self.width,self.height) = self.GetClientSizeTuple()
        xScale = float(self.width) / float(self.minWidth)
        
        dc = wx.wxPaintDC(self)
        dc.BeginDrawing()

        # Draw center line
        dc.SetPen(self.dashPen)
        dc.DrawLine(0,(self.height+0.5)/2,self.width-1,(self.height+0.5)/2)
        
        # Draw envelope segments
        if isEnabled:
            dc.SetPen(self.bluePen)
            dc.SetBrush(self.blueBrush)
        else:
            dc.SetPen(self.greyPen)
            dc.SetBrush(self.greyBrush)

        i = 0
        leftX = 0
        stop = len(self.visibleParams) - 4
        
        if i <= stop:
            leftXParam = self.visibleParams[i]
            leftYParam = self.visibleParams[i+1]
            leftX += int(xScale * leftXParam.getData() + 5)
            leftY = ((self.height+0.5)/2)-leftYParam.getData() + 2
            dc.DrawRectangle(leftX-5,leftY-5,9,9)
            self.points = [(leftX,leftY)]
        
        while i <= stop:
            # Get the x,y params
            rightXParam = self.visibleParams[i+2]
            rightYParam = self.visibleParams[i+3]
            
            # Compute the end points
            rightX = int(leftX + xScale * rightXParam.getData())
            rightY = ((self.height+0.5)/2)-rightYParam.getData() + 2
            
            # Draw the line and handle
            dc.DrawLine(leftX,leftY,rightX,rightY)
            dc.DrawRectangle(rightX-5,rightY-5,9,9)

            # Shift right
            leftX = rightX
            leftY = rightY
            self.points.append((leftX,leftY))
            i += 2
        
        dc.EndDrawing()
        
    def DoDrag(self,mousePoint):
        'Process drag event'
        if self.drag == 0:
            self.drag = 1
            
            # Moving right increases the x component
            xMotion = mousePoint.x - self.lastPoint.x
            # Moving up decreases the y component
            yMotion = self.lastPoint.y - mousePoint.y
            
            if xMotion or yMotion:
                # If this is the first motion since mouseDown
                # then we need to figure out which handle the 
                # user is trying to move because more than one 
                # handle can occupy the same space.
                if self.paramIndex < 0:
                    # Get list of candidate points
                    candidates = []
                    for i in range(len(self.points)):
                        point = self.points[i]
                        if point[0] - 4 <= self.lastPoint.x <= point[0] + 4 \
                           and point[1] -4 <= self.lastPoint.y <= point[1] + 4:
                            candidates.append(i)
                            
                    if len(candidates) > 0:
                        if xMotion < 0:
                            # Pick the first one if moving to the left
                            index = candidates[0]
                        else:
                            # else pick the last one
                            index = candidates[-1]
                            
                        # Params are treated as an (x,y) pair
                        self.paramIndex = index * 2
                        
                if self.paramIndex >= 0:
                    # A set of (x,y) parameters has been identified
                    xParam = self.visibleParams[self.paramIndex]
                    yParam = self.visibleParams[self.paramIndex+1]
                    
                    # Adjust the param values
                    if xMotion:
                        xParam.setData(xParam,xParam.getData() + xMotion)
                    if yMotion:
                        yParam.setData(yParam,yParam.getData() + yMotion)

                    # Force a refresh with the new values
                    self.RefreshValue(self)
                        
            # Remember the new last point
            self.lastPoint = mousePoint
        
            # Done processing
            self.drag = 0
       
    def GetBestSize(self):
        self.width = 0
        self.height = 0
        count = len(self.visibleParams)
        for i in range(0,count-1,2):
            xParam = self.visibleParams[i]
            yParam = self.visibleParams[i+1]
            self.width += (xParam.getMax() - xParam.getMin())
            maxY = yParam.getMax()
            minY = yParam.getMin()
            if (maxY > 0 and minY > 0) or (maxY < 0 and minY < 0):
                self.height = max(self.height, 2 * max(maxY, minY))
            else:
                self.height = max(self.height, abs(maxY) + abs(minY))
        self.width += 13
        self.height += 13
        
        if self.width <= 0 or self.height <= 0:
            self.width = 513
            self.height = 213
        
        return (self.width,self.height)
    
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxControl.Enable(self,flag)
        self.Refresh()
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        self.Enable(flag)
        self.Refresh()
    
# Todo: implement a gauge with a start and stop value
class GaugeWidget(WidgetBase,wx.wxControl):
    'Gauge widget'
    def __init__(self,parent,env,element,patch,init):
        'GaugeWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        self.min = self.getMin()
        self.max = self.getMax()
        width = self.max - self.min + 1
        
        # Add the gauge
        wx.wxControl.__init__(self,parent,-1,wx.wxDefaultPosition,(width,25),style=wx.wxBORDER_NONE)

        # Set tool tip
        self.SetTip(self)
        
        # Event handlers
        wx.EVT_PAINT(self,self.OnPaint)
#        wx.EVT_LEFT_DOWN(self,self.OnMouseDown)
#        wx.EVT_LEFT_UP(self,self.OnMouseUp)
#        wx.EVT_MOTION(self,self.OnMotion)
#        wx.EVT_ENTER_WINDOW(self,self.OnEnterWindow)
        # EVT_SET_FOCUS doesn't seem to work here so I put the property
        # viewer activate into EVT_LEFT_DOWN instead
        wx.EVT_SET_FOCUS(self,self.OnFocus)
#        wx.EVT_KILL_FOCUS(self,self.OnKillFocus)
        
        # Construct pens and brushes
        self.background = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_WINDOW)
        highlight = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_HIGHLIGHT)
        grey = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_GRAYTEXT)
        outline = wx.wxSystemSettings_GetColour(wx.wxSYS_COLOUR_WINDOWTEXT)
        self.bluePen = wx.wxPen(outline,2)
        self.greyPen = wx.wxPen(grey,2)
        self.blueBrush = wx.wxBrush(highlight,wx.wxSOLID)	
        self.greyBrush = wx.wxBrush(grey,wx.wxSOLID)	
        
    def OnPaint(self,event):

        isEnabled = self.IsEnabled()
        if isEnabled:
            self.SetBackgroundColour(self.background)
        else:
            parent = self.GetParent()
            self.SetBackgroundColour(parent.GetBackgroundColour())
            
        dc = wx.wxPaintDC(self)
        dc.BeginDrawing()

        # Draw envelope segments
        if isEnabled:
            dc.SetPen(self.bluePen)
            dc.SetBrush(self.blueBrush)
        else:
            dc.SetPen(self.greyPen)
            dc.SetBrush(self.greyBrush)

        (width,height) = self.GetClientSizeTuple()
        
        scale = float(width) / float(self.max-self.min)
        begin = int(self.params[0].getData() * scale)
        end = int((self.params[1].getData() + 1) * scale)
        
        dc.DrawRectangle(begin,0,end-begin,25)
        
        dc.EndDrawing()
        
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxControl.Enable(self,flag)
        self.Refresh()
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        self.Enable(flag)

class LabelWidget(WidgetBase,wx.wxStaticText):
    'Standalone label'
    def __init__(self,parent,env,element,patch,init):
        'LabelWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        # Add the label
        caption = self.getCaption() + ':'
        wx.wxStaticText.__init__(self,parent,-1,caption)

        self.SetForegroundColour(parent.GetForegroundColour())
        self.SetBackgroundColour(parent.GetBackgroundColour())
        
        # Set tool tip
        self.SetTip(self)
        
        # Event handlers
        wx.EVT_SET_FOCUS(self,self.OnFocus)

    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxStaticText.Enable(self,flag)
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            strval = self.getCurrentVal()
            self.SetValue(strval)
        
class RadioWidget(WidgetBase,wx.wxRadioBox):
    'Radiobox widget'
    def __init__(self,parent,env,element,patch,init):
        'RadioWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        caption = self.getCaption()
        
        # Get the list of items
        items = self.getList()
        if not items:
            items = ['Missing','Missing','Missing']

        # Get the orientation
        layout = self.getLayout()
        if layout == 'horizontal':
            orient = wx.wxRA_SPECIFY_ROWS
        else:
            orient = wx.wxRA_SPECIFY_COLS
            
        # Add the radio box
        wx.wxRadioBox.__init__(self,parent,-1,caption,choices=items,\
                               majorDimension=1,style=orient)

        self.SetForegroundColour(parent.GetForegroundColour())
        self.SetBackgroundColour(parent.GetBackgroundColour())
        
        # Set the selection
        intdata = self.getData()
        self.SetSelection(intdata)
        
        # Set tool tip
        self.SetTip(self)
        
        # Event handlers
        wx.EVT_RADIOBOX(self,self.GetId(),self.OnClick) 
        wx.EVT_SET_FOCUS(self,self.OnFocus)
    
    def OnClick(self,event):
        # Since EVT_RADIOBOX takes precedence over EVT_SET_FOCUS
        # refresh the property view here
        if self.env.property:
            self.env.property.UpdatePropertyList(self)
            
        intdata = self.GetSelection()
        self.setData(self,intdata)
    
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxRadioBox.Enable(self,flag)
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            intdata = self.getData()
            self.SetSelection(intdata)

class SliderWidget(WidgetBase,wx.wxControl):
    'Slider widget'
    def __init__(self,parent,env,element,patch,init):
        'SliderWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        wx.wxControl.__init__(self,parent,-1,style=wx.wxBORDER_NONE)
        self.SetBackgroundColour(parent.GetBackgroundColour())

        # Get the orientation
        self.layout = self.getLayout()
        if self.layout == 'vertical':
            sizerLayout = wx.wxVERTICAL
            sliderLayout = wx.wxSL_VERTICAL
            size = (40,100)
        else:
            sizerLayout = wx.wxHORIZONTAL
            sliderLayout = wx.wxSL_HORIZONTAL
            size = (100,25)
            
        # Get min/max values
        self.mindata = self.getMin()
        self.maxdata = self.getMax()
        self.meandata = (self.maxdata+self.mindata)/2.0
        
        # Create a sizer
        self.sizer = wx.wxBoxSizer(sizerLayout)
        
        # Add the textbox
        self.edit = wx.wxTextCtrl(self,-1,'',\
                style=wx.wxTE_PROCESS_ENTER)
        
        # Adjust the size for best fit
        maxChars = self.getMaxChars()
        width = maxChars * (self.edit.GetCharWidth() + CHAR_WIDTH_PAD)
        self.edit.SetSize((width,-1))
        self.sizer.AddWindow(self.edit,0,SIZER_FORMAT,0)
    
        # Add the slider
        self.slider = wx.wxSlider(self,-1,self.meandata,self.mindata,\
                             self.maxdata,wx.wxDefaultPosition,size,\
                             sliderLayout|wx.wxSL_AUTOTICKS)
        self.slider.SetBackgroundColour(parent.GetBackgroundColour())
        self.sizer.AddWindow(self.slider,1,SIZER_FORMAT,0)
    
        self.SetSizerAndFit(self.sizer)
        self.Layout()

        # Set the slider to the current value
        self.UpdateSlider(self)
                
        # Set tool tip
        self.SetTip(self.edit)
        self.SetTip(self.slider)
        #tip = self.edit.GetToolTip()
        #if tip:
            #self.slider.SetToolTip(tip)
        
        # Event handlers
        #wx.EVT_COMMAND_SCROLL(self.slider,self.GetId(),self.OnScroll)
        wx.EVT_SCROLL(self.slider,self.OnScroll)
        # EVT_LEFT_DCLICK doesn't seem to work on wxSlider
        wx.EVT_LEFT_DCLICK(self.slider,self.OnDoubleClick)
        wx.EVT_SET_FOCUS(self.slider,self.OnFocus)

        wx.EVT_TEXT_ENTER(self.edit,self.edit.GetId(),self.OnEnter)
        wx.EVT_CHAR(self.edit,self.OnChar)
        wx.EVT_SET_FOCUS(self.edit,self.OnFocus)
        wx.EVT_LEFT_DCLICK(self.edit,self.OnDoubleClick)
        
        # Change the cursor to indicate that user can move the handle
        self.slider.SetCursor(wx.wxStockCursor(wx.wxCURSOR_HAND))
        
    def OnChar(self,event):
        key = event.KeyCode()
        if key == wx.WXK_UP or key == wx.WXK_NUMPAD_ADD:
            # Increment value
            self.setData(self,self.getData()+1)
            self.UpdateSlider(self)
        elif key == wx.WXK_DOWN or key == wx.WXK_NUMPAD_SUBTRACT:
            # Decrement value
            self.setData(self,self.getData()-1)
            self.UpdateSlider(self)
        elif key == wx.WXK_HOME:
            # Min value
            self.setData(self,self.getMin())
            self.UpdateSlider(self)
        elif key == wx.WXK_END:
            # Max value
            self.setData(self,self.getMax())
            self.UpdateSlider(self)
        else:
            # Use default handler
            event.Skip()
            
    def OnDoubleClick(self,event):
        'Double click should set the value to the mean'
        self.setData(self,int(self.meandata))
        self.UpdateSlider(self)
    
    def OnEnter(self,event):
        'Try to interpret the entered value'
        strval = self.edit.GetValue()
        try:
            intdata = self.getDataFromVal(strval)
        except:
            intdata = self.getData()
        self.setData(self,intdata)
        self.UpdateSlider(self)
        
    def OnScroll(self,event):
        'Update the value from the slider handle position'
        # Scroll events can be generated when the 
        # handle position has not changed.
        # Only bother if the value has changed
        dataval = self.slider.GetValue()
        dataval = self.Twiddle(dataval)
        currentVal = self.getData()
        if dataval != currentVal:
            self.setData(self,dataval)
            self.UpdateSlider(self)
        
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxControl.Enable(self,flag)
        self.slider.Enable(flag)
        self.edit.Enable(flag)
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            self.UpdateSlider(source)
        
    def Twiddle(self,value):
        'Workaround for vertical slider working backwards'
        if self.layout == 'vertical':
            deviation = self.meandata - value
            val = int(self.meandata + deviation)
        else:
            val = value
        return val

    def UpdateSlider(self,source):
        'Update the edit box and slider with the current value'
        # Update the edit box
        strval = self.getCurrentVal()
        self.edit.SetValue(strval)
        
        # Update the slider
        dataval = self.getData()
        dataval = self.Twiddle(dataval)
        self.slider.SetValue(dataval)

# define to implement auto-repeat on the spinner buttons
SPINBUTTON_REPEAT = 1

class SpinWidget(WidgetBase,wx.wxControl):
    'Spinner widget that supports a variety of data types and formats'
    def __init__(self,parent,env,element,patch,init):
        'SpinWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        
        # Used for SPINBUTTON_REPEAT
        self.increment = 0

        wx.wxControl.__init__(self,parent,-1,style=wx.wxBORDER_NONE)
        
        self.SetBackgroundColour(parent.GetBackgroundColour())

      # Add a sizer to size the edit box and buttons
        self.sizer = wx.wxBoxSizer(wx.wxHORIZONTAL)
        
        # Add the edit control
        self.edit = wx.wxTextCtrl(self,-1,'', style=wx.wxTE_PROCESS_ENTER)
        
        # Bind the enter key to update the value
        wx.EVT_TEXT_ENTER(self,self.edit.GetId(),self.OnEnter)

        # Adjust the size for best fit
        maxChars = self.getMaxChars()
        width = maxChars * (self.edit.GetCharWidth() + CHAR_WIDTH_PAD)
        self.edit.SetSize((width,-1))
        self.SetSize((width+20,24))

        # Put the edit box in the spin sizer
        self.sizer.AddWindow(self.edit,0,SIZER_FORMAT,0)

        self.buttonsizer = wx.wxBoxSizer(wx.wxVERTICAL)

        # Add the increment button
        self.upbutton = wx.wxButton(self,-1,'+',(width,0),(20,12))
        upId = self.upbutton.GetId()
        self.buttonsizer.AddWindow(self.upbutton,1,SIZER_FORMAT,0)

        # Bind the button to the edit box
        if not SPINBUTTON_REPEAT:
            wx.EVT_BUTTON(self.upbutton,upId,self.OnUpButtonClick)

        # Add the decrement button
        self.downbutton = wx.wxButton(self,-1,'-',(width,12),(20,12))
        downId = self.downbutton.GetId()
        self.buttonsizer.AddWindow(self.downbutton,1,SIZER_FORMAT,0)

        # Bind the button to the edit box
        if not SPINBUTTON_REPEAT:
            wx.EVT_BUTTON(self.downbutton,downId,self.OnDownButtonClick)

        # Put the button sizer in the spin sizer
        self.sizer.AddSizer(self.buttonsizer,1,SIZER_FORMAT,0)

        # Attach the spin sizer to self
        self.SetSizerAndFit(self.sizer)
        self.SetAutoLayout(1)

        # Set the widget value to match the data
        strval = self.getCurrentVal()
        self.edit.SetValue(strval)
        
        # Set tool tips
        self.SetTip(self.edit)
        self.SetTip(self.upbutton)
        self.SetTip(self.downbutton)
        #tip = self.edit.GetToolTip()
        #if tip:
            #self.upbutton.SetToolTip(tip)
            #self.downbutton.SetToolTip(tip)
        
        # Other event handlers
        wx.EVT_CHAR(self.edit,self.OnChar)
        wx.EVT_SET_FOCUS(self,self.OnFocus)
        wx.EVT_KILL_FOCUS(self,self.OnKillFocus)

        if SPINBUTTON_REPEAT:
            # Handle mouse up and down events from the buttons
            wx.EVT_LEFT_DOWN(self.upbutton,self.OnMouseDown)
            wx.EVT_LEFT_UP(self.upbutton,self.OnMouseUp)
            wx.EVT_LEFT_DOWN(self.downbutton,self.OnMouseDown)
            wx.EVT_LEFT_UP(self.downbutton,self.OnMouseUp)

            # Use a timer to simulate key repeat
            self.timerId = wx.wxNewId()
            self.timer = wx.wxTimer(self,self.timerId)
            wx.EVT_TIMER(self,self.timerId,self.OnTimer)
        
    def OnUpButtonClick(self,event):
        self.SetSpinVal(self,self.getData()+1)
    
    def OnDownButtonClick(self,event):
        self.SetSpinVal(self,self.getData()-1)
        
    def OnChar(self,event):
        key = event.KeyCode()
        if key == wx.WXK_UP or key == wx.WXK_ADD:
            self.SetSpinVal(self,self.getData()+1)
        elif key == wx.WXK_DOWN or key == wx.WXK_SUBTRACT:
            self.SetSpinVal(self,self.getData()-1)
        elif key == wx.WXK_HOME:
            self.SetSpinVal(self,self.getMin())
        elif key == wx.WXK_END:
            self.SetSpinVal(self,self.getMax())
        else:
            event.Skip()
    
    def OnEnter(self,event):
        strval = self.edit.GetValue()
        try:
            dataval = self.getDataFromVal(strval)
        except:
            dataval = self.getData()
        self.SetSpinVal(self,dataval)

    def OnKillFocus(self,event):
        if SPINBUTTON_REPEAT:
            self.increment = 0
            self.timer.Stop()

    def OnMouseDown(self,event):
        if SPINBUTTON_REPEAT:
            # Find out which button received the event
            id = event.GetId()
            if id == self.upbutton.GetId():
                # up button = increment
                self.SetSpinVal(self,self.getData()+1)
                self.increment = 1
            elif id == self.downbutton.GetId():
                # down button = decrement
                self.SetSpinVal(self,self.getData()-1)
                self.increment = (-1)
            
            # Start the timer one-shot for a 1/2 second delay
            self.timer.Start(500,1)
            
        # Permit normal processing. If this step is not done, the 
        # button image may not highlight
        event.Skip()

    def OnMouseUp(self,event):
        if SPINBUTTON_REPEAT:
            self.increment = 0
            self.timer.Stop()
            
        # Permit normal processing. If this step is not done, the 
        # button image will never return to the "unclicked" state
        event.Skip()
        
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxControl.Enable(self,flag)
        self.edit.Enable(flag)
        self.upbutton.Enable(flag)
        self.downbutton.Enable(flag)
        return flag
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            strval = self.getCurrentVal()
            self.edit.SetValue(strval)
        
    def OnTimer(self,event):
        'Simulates key repeat when holding mouse down on buttons'
        if event.GetId() == self.timerId:
            if self.timer.IsOneShot():
                # The initial 1/2 second delay has passed
                self.timer.Stop()
                # Start repeating 20x/second
                self.timer.Start(50)
            else:
                # Repeat the last increment
                self.SetSpinVal(self,self.getData()+self.increment)

    def SetSpinVal(self,source,intval):
        self.setData(source,intval)
        strval = self.getCurrentVal()
        self.edit.SetValue(strval)

class TextWidget(WidgetBase,wx.wxTextCtrl):
    'Textbox widget'
    def __init__(self,parent,env,element,patch,init):
        'TextWidget constructor'
        WidgetBase.__init__(self,env,element,patch,init)

        # Get the current value
        value = self.getCurrentVal()
        
        # Add the text control
        wx.wxTextCtrl.__init__(self,parent,-1,value,\
            style=wx.wxTE_PROCESS_ENTER|wx.wxTE_READONLY)

        # Adjust the size for best fit
        maxChars = self.getMaxChars()
        width = maxChars * (self.GetCharWidth() + CHAR_WIDTH_PAD)
        self.SetSize((width,-1))
        
        # Set tool tip
        self.SetTip(self)
        
        # Event handlers
        wx.EVT_SET_FOCUS(self,self.OnFocus)
        # Uncomment next line to enable popup list control
        #wx.EVT_LEFT_DOWN(self,self.OnMouseDown)
        
    def OnMouseDown(self,event):
        items = self.getList()
        intval = self.getData()
        param = self.params[-1]
        pos = self.ClientToScreenXY(event.m_x,event.m_y)
        listctl = PopupList(self.GetParent(),-1,pos,items,intval,param)
                                
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        wx.wxTextCtrl.Enable(self,flag)
        return flag

    def RefreshValue(self,source,flag=wx.true):
        flag = self.Enable(flag)
        if flag:
            value = self.getCurrentVal()
            self.SetValue(value)

class GroupWidget(WidgetBase):
    'Custom box sizer that manages (Show,Enable) children'
    def __init__(self,parent,env,element=EMPTY_ELEMENT,patch=None,init=0):
        'Group constructor'
        WidgetBase.__init__(self,env,element,patch,init)
        self.group = None
        self._children = []
            
    def AddChild(self,child):
        self._children.append(child)
        
    def SetParent(self,group):
        self.group = group

    def RemoveChild(self,child):
        del self._children[child]
        
    def GetChildren(self):
        return self._children
        
    def InitChildren(self):
        for child in self._children:
            if hasattr(child,'InitChildren'):
                # Child is a group
                child.InitChildren()
            elif hasattr(child,'initData'):
                # Child is a widget
                child.initData()

    def CheckEnable(self,flag=1):
        if flag:
            if self.group:
               flag = self.group.CheckEnable()
            if flag:
                flag = WidgetBase.CheckEnable(self)
        return flag
        
    def Enable(self,flag=wx.true):
        flag = self.CheckEnable(flag)
        for child in self._children:
            try:
                child.Enable(flag)
            except:
                pass
        
    def RefreshValue(self,source,flag=wx.true):
        flag = self.CheckEnable(flag)
        for child in self._children:
            try:
                child.RefreshValue(source,flag)
            except:
                pass
        
    def Show(self,flag=wx.true):
        self.ShowChildren(flag)

class PopupList(wx.wxSingleChoiceDialog):
    def __init__(self,parent,id,pos,items,selection,param):
        self.param = param
        self.selection = selection
        
        (x,y) = pos
        pos = (max(0,x-200),max(0,y-100))
        
        wx.wxSingleChoiceDialog.__init__(self,parent,'Old Value = %s' % items[selection],\
                             'Select a New Value',pos=pos,choices=items,\
                             style=wx.wxOK|wx.wxCANCEL)

        self.SetSelection(selection)
                
        self.Move(pos)
        ret = self.ShowModal()
        if ret:
            self.param.setData(self,self.GetSelection())            

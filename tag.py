#-----------------------------------------------------------------------------
# Name:        tag.py
# Purpose:     Custom html tag handlers
#
# Author:      John Bair
#
# Created:     2002/10/03
# RCS-ID:      $Id: tag.py $
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
# Note: This module was derived from wxpTag.py in the wxPython distribution
# so the wxPython license applies to the derived code in this module.
#-----------------------------------------------------------------------------

'''
This module parses and processes SynthEd specific tags in a wxHtmlWindow.

Import this module before creating any PatchEditTab objects.

The following tags are handled:

    <WIDGET class="classname" [width="num"] [height="num"]>
        <PARAMETER id="parameterId" [indexer="true|false"]>
        ...
    </WIDGET>

'''

import string
import types

from wx import *
from wx.html import *
from wx.lib.wxpTag import *
from xml2obj import *

import parameter

WIDGET_TAG = 'WIDGET'
PARAM_TAG = 'PARAMETER'

class TagHandler(wxpTagHandler):
    def __init__(self):
        wxpTagHandler.__init__(self)
        self.stack = []
        
    def GetSupportedTags(self):
        return WIDGET_TAG+','+PARAM_TAG

    def HandleTag(self, tag):
        name = tag.GetName()
        if name == WIDGET_TAG:
            return self.HandleWidgetTag(tag)
        elif name == PARAM_TAG:
            return self.HandleParameterTag(tag)
        else:
            raise ValueError, 'unknown tag: ' + name

    def HandleWidgetTag(self, tag):
        
        # create a new context object
        context = _Context()
            
        # find and import the module
        modName = ''
        if tag.HasParam('MODULE'):
            modName = tag.GetParam('MODULE')
        if modName:
            context.classMod = _my_import(modName)
        else:
            context.classMod = parameter

        # find and verify the class
        if not tag.HasParam('CLASS'):
            raise AttributeError, 'WIDGET element requires a "CLASS" attribute'

        className = tag.GetParam('CLASS')
        context.classObj = getattr(context.classMod, className)
        if type(context.classObj) != types.ClassType:
            raise TypeError, 'WIDGET attribute "CLASS" must name a class'

        # now look for width and height
        width = -1
        height = -1
        if tag.HasParam('WIDTH'):
            width = tag.GetParam('WIDTH')
            if width[-1] == '%':
                context.floatWidth = string.atoi(width[:-1], 0)
                #width = context.floatWidth
            else:
                width = string.atoi(width)
        else:
            context.floatWidth = 100
            
        if tag.HasParam('HEIGHT'):
            height = string.atoi(tag.GetParam('HEIGHT'))
        
        #if width > -1 or height > -1:
        #    context.kwargs['size'] = wxSize(width, height)

        # Parse all attributes
        strval = tag.GetAllParams()
        attributes = _param2dict(strval)

        # push context onto stack
        self.stack.append(context)

        # parse up to the closing tag, including any nested tags.
        self.ParseInner(tag)
            
        # pop context off of stack
        self.stack.pop()

        # create the object
        parent = self.GetParser().GetWindow()
        if parent:
            element = Element(className,attributes,context.params)
            obj = apply(context.classObj,
                        (parent,parent.env,element,parent.patch,parent.reset,),
                        context.kwargs)

            if className != 'GroupWidget':
                # add it to the HtmlWindow
                container = self.GetParser().GetContainer()
                cell = wxHtmlWidgetCell(obj, context.floatWidth)
                container.InsertCell(cell)
                obj.SetWidgetCell(cell)

            # Add obj to parent element
            if self.stack:
                parentContext = self.stack[-1]
                parentContext.children.append(obj)
            else:
                parent.group.AddChild(obj)
                if hasattr(obj,'SetParent'):
                    obj.SetParent(parent.group)
            
            # Process any children of this obj
            if hasattr(obj,'InitChildren'):
                for child in context.children:
                    obj.AddChild(child)
                    if hasattr(child,'SetParent'):
                        child.SetParent(obj)
                
        return true

    def HandleParameterTag(self, tag):
        if not tag.HasParam('ID'):
            return false

        params = tag.GetAllParams()
        attributes =  _param2dict(params)
        
        children = []

        element = Element('parameter',attributes,children)
        if len(self.stack) > 0:
            context = self.stack[-1]
            context.params.append(element)
        else:
            id = attributes.get('id')
            msg = 'Standalone <parameter id=%s> is illegal' % id
            raise(str.encode(msg))

        return false

class _Context:
    def __init__(self):
        self.kwargs = {}
        self.width = -1
        self.height = -1
        self.classMod = None
        self.classObj = None
        self.floatWidth = 0
        self.obj = None
        self.params = []
        self.children = []

#----------------------------------------------------------------------
# Function to assist with importing packages
def _my_import(name):
    mod = __import__(name)
    components = string.split(name, '.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


#----------------------------------------------------------------------
# Function to parse a param string (of the form 'item=value item2="value etc"'
# and creates a dictionary
def _param2dict(param):
    i = 0; j = 0; s = len(param); d = {}
    while 1:
        while i<s and param[i] == " " : i = i+1
        if i>=s: break
        j = i
        while j<s and param[j] != "=": j=j+1
        if j+1>=s:
            break
        word = param[i:j]
        i=j+1
        if (param[i] == '"'):
            j=i+1
            while j<s and param[j] != '"' : j=j+1
            if j == s: break
            val = param[i+1:j]
        elif (param[i] != " "):
            j=i+1
            while j<s and param[j] != " " : j=j+1
            val = param[i:j]
        else:
            val = ""
        i=j+1
        d[word] = val
    return d

#----------------------------------------------------------------------
# Add this tag handler to the HTML parser
HtmlWinParser_AddTagHandler(TagHandler)

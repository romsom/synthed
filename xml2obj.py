# Author:      John Bair
#
# Created:     2002/09/15
# RCS-ID:      $Id: xml2obj.py $
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
# Note: This module was derived from the wxPython distribution
# so the wxPython license applies to the derived code in this module.
#-----------------------------------------------------------------------------

"""
Borrowed from wxPython XML tree demo and modified.
"""

import string
from xml.parsers import expat

"""

class Element:
    'An object to contain all the pertinent info for a parsed XML entity'
    def __init__(self,name,attributes,children):
"""

class Element:
    'An object to contain all the pertinent info for a parsed XML element'
    def __init__(self,name,attributes,children):
        'Element constructor'
        # The element's tag name
        self.name = name
        # The element's attribute dictionary
        self.attributes = attributes
        # The elements cdata
        self.cdata = ''
        # The element's child element list (sequence)
        self.children = children
        
    def AddChild(self,element):
        'Add a reference to a child element'
        self.children.append(element)
        
    def _getAttribute(self,key):
        'Get an attribute value'
        value = self.attributes.get(key)
        if not value:
            value = self.attributes.get(key.upper())
        return value
        
    def getAttribute(self,key,default=None):
        'Get an attribute value'
        if default != None:
            try:
                strval = self._getAttribute(key)
                if len(strval) == 0:
                    strval = default
            except:
                strval = default
        else:
            strval = self._getAttribute(key)
            
        # Workaround sax parser problem with newlines in attributes
        if strval:
            strval = strval.replace('\\n','\n')
        
        return strval
    
    def EvalAttribute(self,key,default=''):
        'Evaluate an attribute as a python expression'
        strval = self.getAttribute(key,default)
        # Any legal python expression is permitted
        if strval:
            value = eval(strval)
        else:
            value = ''
        return value

    def getCaption(self):
        'Build a caption for this element'
        # Use a caption attribute if there is one
        name = self.getAttribute('caption','')
        if not name:
            # else use the id
            name = self.getId()
            if not name:
                # else use the value
                name = self.getAttribute('value','')
                #if not name:
                    ## else use the element tag name
                    #name = self.name
        return name
                    
    def getElements(self,name=''):
        'Get the matching child elements'
        if not name:
            #If no tag name is specified, return the all children
            return self.children
        else:
            # else return only those children with a matching tag name
            elements = []
            for element in self.children:
                if element.name == name:
                    elements.append(element)
            return elements
        
    def getFirstElement(self,name=''):
        'Get the first matching child element'
        elements = []
        if not name:
            #If no tag name is specified, use all children
            elements = self.children
        else:
            # else use only those children with a matching tag name
            elements = []
            for element in self.children:
                if element.name == name:
                    elements.append(element)
                    
        if len(elements) > 0:
            return elements[0]
        else:
            return None
        
    def getId(self):
        'The id attribute of the element'
        return self.getAttribute('id','')
    
    def Search(self,name,id=''):
        'Recursively search for the requested elements'
        elements = []
        
        candidates = self.getElements(name)
        for candidate in candidates:
            if not id:
                elements.append(candidate)
            else:
                key = candidate.getId()
                if key == id:
                    elements.append(candidate)
                
        if not elements:
            for child in self.getElements():
                candidates = child.Search(name,id)
                if candidates:
                    elements.extend(candidates)

        return elements
        
        
    def Index(self,name='',dictionary = {}):
        'Builds a dictionary over self and all child elements'
        id = self.getId()
        if id:
            dictionary.update({id:self})
            
        for element in self.children:
            element.Index(name,dictionary)
            
        return dictionary
    
    def WriteXml(self,indent=0):
        'Write XML from self'
        dest = ('    '*indent) + '<' + self.name
        for key in self.attributes.keys():
            value = self.attributes.get(key)
            dest += ' ' + key + '="' + value + '"'
        if len(self.children) == 0:
            dest += ' />\n'
        else:
            dest += '>\n'
            indent += 1
            for child in self.children:
                dest += child.WriteXml(indent)
            indent -= 1
            dest += ('    '*indent) + '</' + self.name + '>\n'
        return dest
                
# A constant empty element to use as a default argument
EMPTY_ELEMENT = Element('empty',{},[])

class Xml2Obj:
    'XML to Object'
    def __init__(self):
        self.root = None
        self.nodeStack = []
        
    def StartElement(self,name,attributes):
        'SAX start element even handler'
        # Instantiate an Element object
        element = Element(name.encode(),attributes,[])
        # DEBUG try to not use encode
        #element = Element(name,attributes,[])
        
        # Push element onto the stack and make it a child of parent
        if len(self.nodeStack) > 0:
            parent = self.nodeStack[-1]
            parent.AddChild(element)
        else:
            self.root = element
        self.nodeStack.append(element)
        
    def EndElement(self,name):
        'SAX end element event handler'
        #self.nodeStack = self.nodeStack[:-1]
        self.nodeStack.pop()

    def CharacterData(self,data):
        'SAX character data event handler'
        if string.strip(data):
            data = data.encode()
            element = self.nodeStack[-1]
            element.cdata += data
            return

    def Parse(self,filename):
        # Create a SAX parser
        print('parsing XML file: {}'.format(filename))
        Parser = expat.ParserCreate()

        # SAX event handlers
        Parser.StartElementHandler = self.StartElement
        Parser.EndElementHandler = self.EndElement
        Parser.CharacterDataHandler = self.CharacterData

        # Parse the XML File
        self.root = None
        self.nodeStack = []
        ParserStatus = Parser.Parse(open(filename,'r').read(), 1)
        print('parsing done, status: {}'.format(ParserStatus))
        print('root name: {}'.format(self.root.name))
        print('root children: {}'.format(self.root.children))
        print('root children names: {}'.format([c.name for c in self.root.children]))
        # add filename to root node for DEBUG
        self.root.path = filename
        print('==================== root xml ====================')
        print(self.root.WriteXml())
        print('==================== root end ====================')
        return self.root
        

header = """<?xml version="1.0"?>

<!-- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	triton_fx.xml

	This data definition should be compatible with Korg TRITON, pro, 
	proX, Rack and Studio. Korg TRITON LE and KARMA differ slightly, so they 
	can be derived from this definition at a later time.
	
	Copyright (c) 2002 by John Bair. ALL RIGHTS RESERVED.

	This program is free software; you can redistribute it and/or modify it 
	under the terms of the GNU General Public License as published by the 
	Free Software Foundation; either version 2 of the License, or (at your 
	option) any later version.
	
	This program is distributed in the hope that it will be useful, but 
	WITHOUT ANY WARRANTY; without even the implied warranty of 
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
	General Public License for more details.
	
	You should have received a copy of the GNU General Public License 
	along with this program; if not, write to the Free Software Foundation, 
	Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA	
	
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -->

<!DOCTYPE data SYSTEM "../../data.dtd">
"""

ID = 0
SUB_ID = 1
HIGH_OFFSET = 2
HIGH_START = 3
HIGH_STOP = 4
MID_OFFSET = 5
MID_START = 6
MID_STOP = 7
LOW_OFFSET = 8
LOW_START = 9
LOW_STOP = 10
PARAMETER = 11
DATA = 12
VALUE = 13

def PrintByte(offset,start,stop):
    offset = offset.strip()
    start = start.strip()
    stop = stop.strip()
    if offset != '':
        out.write('\t\t<byte offset="' + offset + '"')
        if int(start) != 0 or int(stop) != 7:
            out.write(' bitstart="%s" bitstop="%s"/>\n' % (start,stop))
        else:
            out.write('/>\n')

out = open('triton_fx.xml','w')
out.write(header)
out.write('<data>\n')
first = 1
num = 0
caption = ''
for line in open('TritonEffectsParams.txt').xreadlines():
    line = line.strip()
    fields = line.split('\t')
    
    if len(fields) < 2:
        continue
            
    id = fields[ID]
    subid = fields[SUB_ID]
    if id == 'ID':
        continue
        
    if subid == '':
        num += 1
        caption = fields[PARAMETER].strip()
        if first:
            first = 0
        else:
            out.write('</patch>\n')
        out.write('<patch id="fx_%03d" caption="%s">\n' % (num,caption))
    else:
        try:
            parameter = fields[PARAMETER].strip()
            parameter = parameter.lower()
            parameter = parameter.replace('_','')
            parameter = parameter.replace(' ','_')
            parameter = parameter.replace('/','_')
            parameter = parameter.replace(':','')
            parameter = parameter.replace('[','')
            parameter = parameter.replace(']','')
            parameter = parameter.replace('(','')
            parameter = parameter.replace(')','')
            parameter = parameter.replace('?','')
            parameter = parameter.replace('.','')
            parameter = parameter.replace(',','')
            parameter = 'FX_%03d_%s' % (num,parameter)
            (min,max) = fields[DATA].split('~')
            alt = '%02X' % (int(fields[SUB_ID].strip()))
            out.write('\t<parameter id="%s" alt="%s" min="0x%s" max="0x%s">\n' % \
                  (parameter,alt,min.strip(),max.strip()))
            PrintByte(fields[HIGH_OFFSET],fields[HIGH_START],fields[HIGH_STOP])
            PrintByte(fields[MID_OFFSET],fields[MID_START],fields[MID_STOP])
            PrintByte(fields[LOW_OFFSET],fields[LOW_START],fields[LOW_STOP])
            out.write('\t</parameter>\n')
        except:
            pass
out.write('</data>\n')        
out.close()
        
        
        
  
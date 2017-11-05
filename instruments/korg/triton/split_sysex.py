import os,stat

info = os.stat('mr_flssnds.syx')
length = info[stat.ST_SIZE]
infile = open('mr_flssnds.syx','rb')
while infile.tell() < length:
  header = infile.read(8)
  filename = 'mr_snd%03d.syx' % ord(header[7])
  outfile = open(filename,'wb')
  outfile.write(header)
  c = ''
  while c != '\xF7':
    c = infile.read(1)
    outfile.write(c)
  outfile.close()
infile.close()
  

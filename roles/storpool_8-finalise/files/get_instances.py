import sys
import sp.disk.disklist as d
import sp.tools.cg.cgtool.util.servers as s
for p in s.lst(d.server_instances(True)):
  print ("storpool_" + p)

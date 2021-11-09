import tesp_support.process_eplus as ep
import sys

root='eplus'
title=None
pngfile=None

if len(sys.argv) > 1:
  root = sys.argv[1]
if len(sys.argv) > 2:
  title = sys.argv[2]
if len(sys.argv) > 3:
  pngfile = sys.argv[3]

ep.process_eplus (root, title=title, save_file=pngfile)


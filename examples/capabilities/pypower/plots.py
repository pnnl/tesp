import tesp_support.process_pypower as pp

import sys

root='ppcase'
title=None
save_file=None

if len(sys.argv) > 1:
  root = sys.argv[1]
if len(sys.argv) > 2:
  title = sys.argv[2]
if len(sys.argv) > 3:
  save_file = sys.argv[3]
  
pp.process_pypower (root, title=title, save_file=save_file, save_only=False)


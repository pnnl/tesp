# usage 'python3 make_comm_eplus.py'
import json
import tesp_support.api as tesp

if __name__ == '__main__':
  print ('usage: python3 tabulate_responses.py')
  template_dir = '../../support/comm/'
  tesp.make_gld_eplus_case (fname = 'CommDef.json', template_dir = template_dir)

  # process TMY3 ==> TMY2 ==> EPW
# cmdline = 'TMY3toTMY2_ansi ' + weatherfile + ' > ' + casedir + '/' + rootweather + '.tmy2'
# print (cmdline)
# pw1 = subprocess.Popen (cmdline, shell=True)
# pw1.wait()
# cmdline = pycall + """ -c "import tesp_support.api as tesp;tesp.convert_tmy2_to_epw('""" + casedir + '/' + rootweather + """')" """
# print (cmdline)
# pw2 = subprocess.Popen (cmdline, shell=True)
# pw2.wait()
# os.remove (casedir + '/' + rootweather + '.tmy2')




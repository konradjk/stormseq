#!/usr/bin/env python
import cgi
import os, glob, sys
import commands
import cgitb; cgitb.enable()  # for troubleshooting
import json
from helpers import *

redirect_url = "/"

f = open('/tmp/price_log.txt', 'w')
def get_price(type):
  out = [line for line in commands.getoutput("sudo starcluster shi %s" % type).split('\n') if line.find('price') > -1]
  return '<br/>'.join(out)

form = cgi.FieldStorage()
parameters = json.loads(form.getvalue('all_objects'))
parameters['sample'] = ''
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()

if not os.path.isfile('/root/.starcluster/config') or commands.getstatusoutput('sudo starcluster shi m1.large')[1].find('AuthFailure') > -1:
  write_basic_config_file(parameters, '')

large_price = get_price('m1.large')
hi_mem_price = get_price('m2.4xlarge')
f.write(large_price + '\n' + hi_mem_price)

print 'Content-Type: text/html'
print
sys.stdout.write('%s,%s' % (large_price, hi_mem_price))
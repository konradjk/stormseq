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

if parameters["amazon-instance-types"] == 'default':
	instance_type = instances[parameters['alignment_pipeline']]
else:
	instance_type = parameters["amazon-instance-types"]
f.write(instance_type + '\n')
price = get_price(instance_type)
f.write(price + '\n')

print 'Content-Type: text/html'
print
sys.stdout.write(price)
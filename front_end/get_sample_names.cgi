#!/usr/bin/env python
import cgi
import os, glob, sys
import commands
import cgitb; cgitb.enable()  # for troubleshooting
import json
from helpers import *

redirect_url = "/"

f = open('/tmp/sample_log.txt', 'w')

form = cgi.FieldStorage()
parameters = json.loads(form.getvalue('all_objects'))
parameters['sample'] = ''
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()

if not os.path.isfile('/root/.s3cfg') or commands.getstatusoutput('s3cmd ls')[1].find('ERROR') > -1:
  setup_s3cfg(parameters)

try:
  sample_text = commands.getstatusoutput('s3cmd ls --config /root/.s3cfg s3://%s | grep "\/$"' % parameters['s3_bucket'])[1]
  f.write(sample_text + '\n')
  samples = [x.split()[-1].split('/')[-2] for x in sample_text.split('\n')]
  
  f.write(';'.join(samples) + '\n')
  
  print 'Content-Type: text/html'
  print
  sys.stdout.write(';'.join(samples))
except Exception, e:
  print 'Content-Type: text/html'
  print
  sys.stdout.write('Error getting samples. Check credentials.')
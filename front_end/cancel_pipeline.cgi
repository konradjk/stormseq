#!/usr/bin/env python
import cgi
import os, glob, sys, time, re
import json
import commands, subprocess
from collections import defaultdict
from multiprocessing import Process
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *
import string

form = cgi.FieldStorage()
parameters = json.loads(form.getvalue('all_objects'))

files = glob.glob('/var/www/stormseq_*.cnf')
samples = [re.sub('^stormseq_', '', os.path.splitext(os.path.basename(file))[0]) for file in files]

f = open("/tmp/cancel_log.txt","w")
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()
f.close()

if len(files) == 0:
  generic_response('nothing-to-cancel')
else:
  with open(files[0]) as f:
    input = json.loads(f.readline())
    existing_params = input['parameters']

if existing_params['access_key_id'] != parameters['access_key_id'] or existing_params['secret_access_key'] != parameters['secret_access_key']:
  generic_response('wrong-creds')

exit_status_sum = 0
for sample in samples:
    exit_status, term_stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq_%s' % sample)
    exit_status_sum += exit_status
    exit_status, term_stdout = commands.getstatusoutput('sudo starcluster removekey -c stormseq_starcluster_%s' % sample)
    exit_status_sum += exit_status

deleted_bucket = False
if parameters.get('delete_s3',False):
    exit_status, term_stdout = commands.getstatusoutput('sudo s3cmd rb -rf s3://%s' % parameters['s3_bucket'])
    exit_status_sum += exit_status
    if exit_status == 0:
        deleted_bucket = True

if exit_status_sum:
    generic_response("failure")
elif deleted_bucket:
    generic_response("success_and_deleted")
else:
    generic_response("success")

sys.exit()

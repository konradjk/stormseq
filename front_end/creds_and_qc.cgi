#!/usr/bin/env python
import cgi
import os, glob, sys
import gzip
import json
import commands
from collections import defaultdict
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *

redirect_url = "/"

form = cgi.FieldStorage()
parameters = json.loads(form.getvalue('all_objects'))

f = open("/tmp/qc_log.txt","w")
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()

files, ext = get_files(parameters, f)

file_headers = defaultdict(dict)
# Override open for convenience
# TODO: Add check for end of file, same length read as start (truncated files)
my_open = gzip.open if ext == '.gz' else open
for filename in files:
  with my_open(filename) as fqfile:
    first_line = fqfile.readline().strip().split('/')
    if len(first_line) != 2:
      qc_fail('Malformed paired end file (read name should have /1 or /2 tag)')
    read, pair = first_line
    if read in file_headers and pair in file_headers[read]:
      qc_fail('Duplicate file found')
    file_headers[read][pair] = filename
    read_size = fqfile.readline().strip()
  if ext == '.gz':
    last_line = commands.getoutput('zcat %s | tail -1' % filename)
  else:
    last_line = commands.getoutput('tail -1 %s' % filename)
  if len(read_size) != len(last_line):
    qc_fail('Last line not the same length as 2nd line. Truncated file?')
# Rename to basename_read_1234_1_{1,2}.fq.gz if gzipped, otherwise .fq
# Yes, this may add an unnecessary _1 to the first pair, but worth the hassle
add_ext = '.fq.gz' if ext == '.gz' else '.fq'
for read in file_headers:
  fbase = os.path.splitext(file_headers[read]['1'])[0].replace('.fq', '').replace('.fastq', '')
  os.rename(file_headers[read]['1'], fbase + '_1' + add_ext)
  os.rename(file_headers[read]['2'], fbase + '_2' + add_ext)

number_of_processes = len(files)/2

check_certs_and_setup_env(f)

# Write API keys to config file
write_config_file(parameters, number_of_processes, f)
# Test API keys
exit_status, stdout = commands.getstatusoutput('sudo starcluster lsi')
f.write(stdout + '\n')
if stdout.find('AuthFailure') > -1:
  print 'Content-Type: text/html'
  print
  sys.stdout.write('auth-fail')
  sys.exit()

f.write('Got here!')
f.close()

print 'Content-Type: text/html'
print
sys.stdout.write('success')
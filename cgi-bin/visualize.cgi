#!/usr/bin/env python
import cgi
import os, glob, sys
import gzip, re
import json
import commands, subprocess
from collections import defaultdict
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *

def check_file(sample_name, type):
  check_command = "ls -1 /var/www/%s.%s.stats.tar.gz" % (sample_name, type)
  try:
    stdout = subprocess.check_output(check_command.split(' '))
  except subprocess.CalledProcessError:
    return False
  f.write(stdout + '\n')
  return True

def parse_bam_stats(sample_name, type):
  print "<a href='mydata/%s.%s.stats.insert_size_histogram.pdf' target='_blank'>%s BAM Insert Size Distribution</a><br/>" % (sample_name, type, type.capitalize())
  print "<a href='mydata/%s.%s.stats.quality_by_cycle.pdf' target='_blank'>%s BAM Quality by Cycle</a><br/>" % (sample_name, type, type.capitalize())
  print "<a href='mydata/%s.%s.stats.quality_distribution.pdf' target='_blank'>%s BAM Mapping Quality Distribution</a><br/>" % (sample_name, type, type.capitalize())
  #with "/var/www/mydata/%s.%s.stats.alignment_summary_metrics" % (sample_name, type) as stats_file:
  #  pass

def parse_vcf_eval(sample_name):
  pass

redirect_url = "/"

f = open("/tmp/vis_log.txt","w")
form = cgi.FieldStorage()
sample_name = json.loads(form.getvalue('sample_name'))

print 'Content-Type: text/html'
print
if check_file(sample_name, 'merged'):
  parse_bam_stats(sample_name, 'merged')
if check_file(sample_name, 'final'):
  parse_bam_stats(sample_name, 'final')
if check_file(sample_name, 'vcf'):
  parse_vcf_eval(sample_name)
  

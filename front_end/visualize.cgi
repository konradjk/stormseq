#!/usr/bin/env python
import cgi
import os, glob, sys
import gzip, re
import json
import commands, subprocess
from collections import defaultdict
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *

def check_file(file):
  check_command = "ls -1 /var/www/%s" % (file)
  try:
    stdout = subprocess.check_output(check_command.split(' '))
  except subprocess.CalledProcessError:
    return False
  f.write(stdout + '\n')
  return True

def parse_bam_stats(sample_name, type):
  print "<div class='%s-stats'><em>%s stats:</em><br/>" % (type, type.capitalize())
  print "<a href='mydata/%s.%s.stats.insert_size_histogram.pdf' target='_blank'>%s BAM Insert Size Distribution</a><br/>" % (sample_name, type, type.capitalize())
  print "<a href='mydata/%s.%s.stats.quality_by_cycle.pdf' target='_blank'>%s BAM Quality by Cycle</a><br/>" % (sample_name, type, type.capitalize())
  print "<a href='mydata/%s.%s.stats.quality_distribution.pdf' target='_blank'>%s BAM Mapping Quality Distribution</a><br/>" % (sample_name, type, type.capitalize())
  print "</div><br/>"
  #with "/var/www/mydata/%s.%s.stats.alignment_summary_metrics" % (sample_name, type) as stats_file:
  #  pass

def parse_vcf_eval(file, parameters):
  print "<em>VCF statistics:</em><br/>"
  with open(file) as f:
    raw_data = f.readlines().split('\n')
  variants = dict([(line.split()[4], line.strip()[11]) for line in raw_data if line.startswith('CountVariants')])
  try:
    percent_novel = 100*float(variants['novel'])/float(variants['all'])
    print 'Called %s SNPs, out of which %s (%.2f) were novel (i.e. not found in %s)<br/>' % (variants['all'], variants['novel'], percent_novel, parameters['dbsnp_version'])
    titv = dict([(line.split()[4], line.strip()[7]) for line in raw_data if line.startswith('TiTvVariantEvaluator')])
    print 'Ti/Tv ratio: %s (%s for novel variants)<br/>' % (titv['all'], titv['novel'])
  except ZeroDivisionError:
    print 'No SNPs called<br/>'

def parse_indel_vcf_eval(file, parameters):
  indels = {}
  print "<em>Indel statistics:</em><br/>"
  with open(file) as f:
    raw_data = f.readlines().split('\n')
  insertions = dict([(line.split()[4], line.strip()[13]) for line in raw_data if line.startswith('CountVariants')])
  deletions = dict([(line.split()[4], line.strip()[14]) for line in raw_data if line.startswith('CountVariants')])
  total = dict([(type, int(insertions['type']) + int(deletions['type'])) for type in insertions])
  
  try:
    percent_novel = 100*float(total['novel'])/float(total['all'])
    print 'Called %s indels, out of which %s (%.2f) were novel (i.e. not found in %s)<br/>' % (total['all'], total['novel'], percent_novel, parameters['dbsnp_version'])
  except ZeroDivisionError:
    print 'No indels called<br/>'
    return
  
  try:
    percent_novel = 100*float(insertions['novel'])/float(insertions['all'])
    print 'Called %s insertions, out of which %s (%.2f) were novel (i.e. not found in %s)<br/>' % (insertions['all'], insertions['novel'], percent_novel, parameters['dbsnp_version'])
  except ZeroDivisionError:
    print 'No insertions called<br/>'
  
  try:
    percent_novel = 100*float(deletions['novel'])/float(deletions['all'])
    print 'Called %s deletions, out of which %s (%.2f) were novel (i.e. not found in %s)<br/>' % (deletions['all'], deletions['novel'], percent_novel, parameters['dbsnp_version'])
  except ZeroDivisionError:
    print 'No deletions called<br/>'

def parse_depth_files(depth_file):
  filename = '%s.depth.sample_cumulative_coverage_proportions' % depth_file
  with open(filename) as f:
    headers = [int(x.replace('gte_', '')) for x in f.readline().strip().split()]
    depths = map(float, f.readline().strip().split()[:-1])
  zip(headers, depths)

redirect_url = "/"

f = open("/tmp/vis_log.txt","w")
form = cgi.FieldStorage()
sample_names = json.loads(form.getvalue('sample_names'))

if len(sample_names) == 0 or sample_names[0] == '':
  generic_response('')

print 'Content-Type: text/html'
print
for sample_name in sample_names:
  config_file = '/var/www/stormseq_%s.cnf' % sample_name
  try:
    with open(config_file) as cnf:
      input = json.loads(cnf.readline())
  except IOError:
    generic_response('nothing')
  parameters = input['parameters']

  print "<h4>%s Results:</h4>" % (sample_name)
  if check_file('%s.merged.stats.tar.gz' % sample_name):
    parse_bam_stats(sample_name, 'merged')
  if check_file('%s.final.stats.tar.gz' % sample_name):
    parse_bam_stats(sample_name, 'final')
    
  if check_file('%s.vcf.eval' % sample_name):
    parse_vcf_eval('%s.vcf.eval' % sample_name, parameters)
    if parameters['indel_calling']:
      parse_indel_vcf_eval('%s.vcf.eval' % sample_name)


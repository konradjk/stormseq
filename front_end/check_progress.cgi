#!/usr/bin/env python
import cgi
import os, glob, sys
import gzip, re
import json
import commands, subprocess
from collections import defaultdict
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *

redirect_url = "/"

f = open("/tmp/checking_log.txt","w")
form = cgi.FieldStorage()
samples = [re.sub('^stormseq_', '', os.path.splitext(os.path.basename(file))[0]) for file in glob.glob('/var/www/stormseq_*.cnf')]

response = {}
for sample_name in samples:
  f.write(sample_name + '\n')
  check_command = ("sudo starcluster sshmaster stormseq_%s" % sample_name).split(' ')
  check_command.append("'ls -1 /mydata/'")
  try:
    stdout = subprocess.check_output(check_command)
  except subprocess.CalledProcessError:
    generic_response('no-progress')
  
  chroms = ['chr%s' % x for x in range(1,23)]
  chroms.extend(['chrX', 'chrY', 'chrM'])
  
  all_files = stdout.split('\n')
  f.write(stdout + '\n')
  files = dict(zip(all_files, len(all_files)*[True]))
  
  with open('/var/www/stormseq_%s.cnf' % sample_name) as cnf:
    input = json.loads(cnf.readline())
  
  bases = [os.path.basename(x['1']) for x in input['files'].values()]
  
  initials = {}
  for base in bases:
    initials[base] = int(base + '.sam' in files)
    initials[base] += int(base + '.raw.bam' in files)
    initials[base] += int(base + '.sorted.bam' in files)
    initials[base] += int(base + '.sorted.bam.done' in files)
  
  cleans = {}
  for chrom in chroms:
    cleans[chrom] = int((sample_name + '_%s.nodup.bam' % chrom) in files)
    cleans[chrom] += int((sample_name + '_%s.align.bam' % chrom) in files)
    cleans[chrom] += int((sample_name + '_%s.recal.bam' % chrom) in files)
    cleans[chrom] += int((sample_name + '_%s.raw.vcf' % chrom) in files) or int((sample_name + '_%s.vcf' % chrom) in files)
    cleans[chrom] += int((sample_name + '_%s.vcf.done' % chrom) in files)
  
  outputs = {}
  outputs['merged'] = int(sample_name + '.merged.bam.done' in files)
  outputs['final'] = int(sample_name + '.final.bam.done' in files)
  outputs['vcf'] = int(sample_name + '.vcf.done' in files)
  
  for key in outputs.keys():
    outfiles = [file for file in all_files if file.find('stormseq') > -1 and file.find(key) > -1]
    outputs[key + '_file'] = outfiles[0] if key and len(outfiles) > 0 else ''
  
  outputs['merged_stats'] = int(sample_name + '.merged.stats.tar.gz' in files)
  outputs['final_stats'] = int(sample_name + '.final.stats.tar.gz' in files)
  outputs['depth'] = int(sample_name + '.depth' in files)
  outputs['vcf_eval'] = int(sample_name + '.vcf.eval' in files)
  
  out = {'initials' : initials, 'cleans' : cleans, 'outputs' : outputs}
  f.write(json.dumps(out))
  response[sample_name] = out

f.close()
  
print 'Content-Type: text/html'
print
sys.stdout.write(json.dumps(response))
sys.exit()
#!/usr/bin/env python
import cgi
import os, glob, sys
import gzip, re
import json
import commands, subprocess
from collections import defaultdict, OrderedDict
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
  if check_file('%s.%s.stats.tar.gz' % (sample_name, type)):
    stats = {
      'Insert Size Distribution': 'mydata/%s.%s.stats.insert_size_histogram.pdf' % (sample_name, type),
      'Quality by Cycle' : 'mydata/%s.%s.stats.quality_by_cycle.pdf' % (sample_name, type),
      'Mapping Quality Distribution' : 'mydata/%s.%s.stats.quality_distribution.pdf' % (sample_name, type)
    }
    #with "/var/www/mydata/%s.%s.stats.alignment_summary_metrics" % (sample_name, type) as stats_file:
    #  pass
    return stats

def parse_vcf_eval(file, parameters):
  if check_file(file):
    with open(file) as f:
      raw_data = f.readlines()
    variants = dict([(line.split()[4], int(line.split()[11])) for line in raw_data if line.startswith('CountVariants') and line.find('Novelty') == -1])
    titv = dict([(line.split()[4], float(line.split()[7])) for line in raw_data if line.startswith('TiTvVariantEvaluator') and line.find('Novelty') == -1])
    return {
      'variants': variants,
      'titv': titv,
      'dbsnp': parameters['dbsnp_version']
    }

def parse_indel_vcf_eval(file, parameters):
  if check_file(file):
    types = ('all', 'novel', 'known')
    with open(file) as f:
      raw_data = f.readlines()
    insertions = dict([(line.split()[4], int(line.split()[13])) for line in raw_data if line.startswith('CountVariants') and line.find('Novelty') == -1])
    deletions = dict([(line.split()[4], int(line.split()[14])) for line in raw_data if line.startswith('CountVariants') and line.find('Novelty') == -1])
    total = dict([(type, int(insertions[type]) + int(deletions[type])) for type in types])
    lengths = defaultdict(dict)
    for line in raw_data:
      if line.startswith('IndelLengthHistogram') and line.find('Novelty') == -1:
        lengths[int(line.split()[5])][line.split()[4]] = float(line.split()[6])
    output_lengths = []
    for length in sorted(lengths.keys()):
      output_lengths.append((length, [lengths[length][type] for type in types]))
    return {
      'insertions' : insertions,
      'deletions' : deletions,
      'total' : total,
      'lengths' : output_lengths
    }

def parse_bam_depth(sample, type):
  filename = '%s%s.depth.sample_statistics' % (sample, type)
  if check_file(filename):
    with open(filename) as f:
      headers = [int(x.split('_')[1]) for x in f.readline().strip().split()[:-1]]
      depths = map(int, f.readline().strip().split()[:-1])
    return zip(headers, depths)

def get_circos_plot(sample):
  if check_file(sample + '_circos.pdf'):
    return [sample + '_circos.png', sample + '_circos.pdf']

def parse_annotation_summary(sample):
  file = sample + '.vcf.annotation_summary'
  if check_file(file):
    with open(file) as f:
      return json.loads(f.read())

redirect_url = "/"

f = open("/tmp/vis_log.txt","w")
sample_names = [re.sub('^stormseq_', '', os.path.splitext(os.path.basename(file))[0]) for file in glob.glob('/var/www/stormseq_*.cnf')]
sample_names.sort()
if 'call_all_samples' in sample_names:
  sample_names.remove('call_all_samples')
  #samples.append('call_all_samples') #TODO

if len(sample_names) == 0 or sample_names[0] == '':
  generic_response('')

print 'Content-Type: text/html'
print
response = OrderedDict()
for sample_name in sample_names:
  finished = check_file('%s.done' % sample_name)
  #if finished and check_file('%s.vis' % sample_name):
  #  response[sample_name] = json.loads(open('%s.vis' % sample_name).read())
  #  continue
  config_file = '/var/www/stormseq_%s.cnf' % sample_name
  try:
    with open(config_file) as cnf:
      input = json.loads(cnf.readline())
  except IOError:
    generic_response('nothing')
  parameters = input['parameters']
  
  sample_stats = {}
  sample_stats['merged_stats'] = parse_bam_stats(sample_name, 'merged')
  sample_stats['final_stats'] = parse_bam_stats(sample_name, 'final')
  
  sample_stats['merged_depth'] = parse_bam_depth(sample_name, '.merged')
  sample_stats['final_depth'] = parse_bam_depth(sample_name, '')
  
  sample_stats['vcf_stats'] = parse_vcf_eval('%s.vcf.eval' % sample_name, parameters)
  sample_stats['snp_density'] = get_circos_plot(sample_name)
  sample_stats['annotation_summary'] = parse_annotation_summary(sample_name)
  sample_stats['indel_stats'] = parse_indel_vcf_eval('%s.vcf.eval' % sample_name, parameters)

  sample_stats['finished'] = finished
  
  #if finished:
  #  with open('%s.vis' % sample_name, 'w') as g:
  #    g.write(json.dumps(sample_stats))
  
  response[sample_name] = sample_stats

sys.stdout.write(json.dumps(response))
sys.exit()
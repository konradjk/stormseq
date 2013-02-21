#!/usr/bin/env python

import sys
import os
import subprocess
from optparse import OptionParser
import json
import re
import time
import commands
from helpers import *

root = '/usr/local/bin/'
parser = OptionParser()
parser.add_option('--config_file', help='Config File (JSON)')

(options, args) = parser.parse_args()

with open(options.config_file) as f:
  input = json.loads(f.readline())

f = open('map_log.txt', 'w')
sample = input['sample']
parameters = input['parameters']
parameters['sample_name'] = sample
try:
  stdout = commands.getoutput('find /mydata/* | grep -v cnf | xargs rm -r')
except Exception, e:
  pass
setup_s3cfg(parameters, '/mydata/.s3cfg')

call_qsub = "qsub -cwd -b y python joint-%(program)s-call.py --samples=%(samples)s --chromosome=%(chrom)s --reference=%(reference)s --dbsnp=%(dbsnp)s %(indels)s %(intervals)s --config_file=" + options.config_file

inputs = {
  'dbsnp' : dbsnp_paths[parameters['dbsnp_version']],
  'reference' : ref_paths[parameters['genome_version']],
  'program': parameters['calling_pipeline'],
  'intervals': '',
  'indels' : '--indels' if parameters['indel_calling'] else ''}

directory = 's3://%s/' % (parameters['s3_bucket'])
command = 'sudo s3cmd -c /mydata/.s3cfg ls %s' % directory
f.write(command + '\n')
file_info = subprocess.check_output(command.split()).strip().split('\n')
print file_info
all_bams = []
for sample in parameters['sample_names']:
  file = ''
  date = 0
  for line in file_info:
    if re.search(sample + '_stormseq_\d+.final.bam', line) is not None:
      print line
      this_date = int(re.sub('.final.bam$', '', line.strip().split()[3]).split('_')[-1])
      if this_date > date:
        date = this_date
        file = line.strip().split()[3].split('/')[-1]
  all_bams.append(file)

inputs['samples'] = ','.join(all_bams)

if inputs['program'] == 'gatk':
    try:
        inputs['stand_call_conf'] = float(parameters['gatk_opt_std_call'])
    except ValueError:
        inputs['stand_call_conf'] = "30.0"
    try:
        inputs['stand_emit_conf'] = float(parameters['gatk_opt_std_emit'])
    except ValueError:
        inputs['stand_emit_conf'] = "30.0"
    call_qsub += ' --stand_call_conf=%(stand_call_conf)s --stand_emit_conf=%(stand_emit_conf)s'
    call_qsub += ' --output_gvcf' if parameters['output_gvcf'] else ''

if parameters['data_type'] == 'type_exome_illumina':
  inputs['intervals'] = '--intervals=/data/intervals/Illumina_TruSeq.50bp.interval_list'

# Run commands
all_jobs = []
chroms = get_chroms()
for chrom in chroms:
  inputs['chrom'] = chrom
  command = call_qsub % inputs
  f.write('%s\n' % command)
  stdout = subprocess.check_output(command.split())
  job = get_job_id(stdout)
  all_jobs.append(job)
  f.write('%s\n' % stdout)

priority = ','.join(chroms)
vcf_merge_command = "qsub -cwd -b y -hold_jid %s python merge-vcf.py --reference=%s --priority=%s --output=/mydata/stormseq_all_samples.vcf" % (','.join(all_jobs), ref_paths[parameters['genome_version']], priority)
f.write(vcf_merge_command)
exit_status, stdout = commands.getstatusoutput(vcf_merge_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

put_file_in_s3('stormseq_all_samples', 'vcf', parameters['s3_bucket'], job, True)

vcf_stats_command = "qsub -hold_jid %s -b y -q all.q@master,all.q@node001 -cwd -N vcfstats python vcf-stats.py %s --reference=%s --dbsnp=%s --input=/mydata/stormseq_all_samples.vcf --output=/mydata/stormseq_all_samples.vcf.eval" % (job, inputs['intervals'], ref_paths[parameters['genome_version']], dbsnp_paths[parameters['dbsnp_version']])
f.write(vcf_stats_command)
exit_status, stdout = commands.getstatusoutput(vcf_stats_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

put_file_in_s3('stormseq_all_samples', 'vcf.eval', parameters['s3_bucket'], job, True)
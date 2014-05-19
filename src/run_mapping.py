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

parser = OptionParser()
parser.add_option('--config_file', help='Config File (JSON)')

(options, args) = parser.parse_args()

with open(options.config_file) as f:
    input = json.loads(f.readline())

try:
    stdout = commands.getoutput('find /mydata/* | grep -v cnf | xargs rm -r')
except Exception, e:
    pass
try:
    os.mkdir('/mydata/logs/')
except OSError, e:
    pass

f = open('/mydata/logs/map_log.txt', 'w')
files = input['files']
sample = input['sample']
parameters = input['parameters']
parameters['sample_name'] = sample
setup_s3cfg(parameters, '/mydata/.s3cfg')

ref = ref_paths[parameters['genome_version']]
all_mapping_jobs = []
all_sorted_bams = []
for read_pair in files.keys():
    s3_fq1 = files[read_pair]['1']
    s3_fq2 = files[read_pair]['2']
    if parameters['alignment_pipeline'] == 'bwa':
        try:
            quality = int(parameters['bwa_opt_q'])
        except ValueError:
            quality = 20
        map_command = "qsub -b y -cwd -R y -l virtual_free=6700M -e /mydata/logs/ -o /mydata/logs/ python bwa-map.py --fq1=%s --fq2=%s --reference=%s --quality=%s --sample=%s --config_file=%s --output=/mydata/" % (s3_fq1, s3_fq2, ref, quality, sample, options.config_file)
    if parameters['alignment_pipeline'] == 'bwa-mem':
        map_command = "qsub -b y -cwd -R y -l virtual_free=6700M -e /mydata/logs/ -o /mydata/logs/ python bwa-mem-map.py --fq1=%s --fq2=%s --reference=%s --sample=%s --config_file=%s --output=/mydata/" % (s3_fq1, s3_fq2, ref, sample, options.config_file,)
    elif parameters['alignment_pipeline'] == 'snap':
        ref_dir = os.path.join(os.path.dirname(ref), 'snap/')
        try:
            d = int(parameters['snap_opt_d'])
        except ValueError:
            d = 15
        try:
            h = int(parameters['snap_opt_h'])
        except ValueError:
            h = 250
        map_command = "qsub -b y -cwd -R y -l h_vmem=60G -e /mydata/logs/ -o /mydata/logs/ python snap-map.py --fq1=%s --fq2=%s --reference=%s --sample=%s --config_file=%s --output=/mydata/" % (s3_fq1, s3_fq2, ref_dir, sample, options.config_file)
    f.write(map_command + '\n')
    stdout = commands.getoutput(map_command)
    f.write(stdout + '\n')
    job = get_job_id(stdout)
    all_mapping_jobs.append(job)
    all_sorted_bams.append(os.path.join('/mydata/', os.path.basename(s3_fq1) + '.sorted.bam'))

merged_bam = sample + '.merged.bam'
merge_command = "qsub -hold_jid %s -e /mydata/logs/ -o /mydata/logs/ -b y -cwd python merge.py --delete --bams=%s --output=/mydata/%s" % (','.join(all_mapping_jobs), ','.join(all_sorted_bams), merged_bam)
exit_status, stdout = commands.getstatusoutput(merge_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

current_date = time.strftime("%Y%m%d", time.gmtime())
bucket_file = '%s_stormseq_%s.merged.stats.tar.gz' % (sample, current_date)
upload_command = "qsub -hold_jid %s -cwd -b y s3cmd -c /mydata/.s3cfg put /mydata/%s s3://%s/%s" % (job, sample + '.merged.stats.tar.gz', parameters['s3_bucket'], bucket_file)
_, stdout = commands.getstatusoutput(upload_command)
job = get_job_id(stdout)

current_date = time.strftime("%Y%m%d", time.gmtime())
bucket_file = '%s_stormseq_%s.merged.bam' % (sample, current_date)
upload_command = "qsub -hold_jid %s -cwd -b y s3cmd -c /mydata/.s3cfg put /mydata/%s s3://%s/%s" % (job, merged_bam, parameters['s3_bucket'], bucket_file)
_, stdout = commands.getstatusoutput(upload_command)
job = get_job_id(stdout)

command = "qsub -hold_jid %s -cwd -b y touch /mydata/%s.done" % (job, merged_bam)
exit_status, stdout = commands.getstatusoutput(command)
f.write('%s\n' % str(stdout))

command = "qsub -hold_jid %s -cwd -b y touch /mydata/%s.done" % (job, sample + '.merged.stats.tar.gz')
exit_status, stdout = commands.getstatusoutput(command)
f.write('%s\n' % str(stdout))
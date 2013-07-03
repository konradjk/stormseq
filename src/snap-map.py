import sys
import os
import re
import json
import boto
from optparse import OptionParser
import commands, subprocess
from multiprocessing import Process
from helpers import *

parser = OptionParser()
parser.add_option('--fq1', help='FASTQ file, pair 1')
parser.add_option('--fq2', help='FASTQ file, pair 2')
parser.add_option('--reference', help='Genome index directory')
parser.add_option('--platform', help='Platform', default='Illumina')
parser.add_option('--sample', help='Sample', default='Me')
parser.add_option('--threads', help='Sample', default=6)
parser.add_option('--output', help='Output directory')
parser.add_option('--config_file', help='Config File (JSON)')

(options, args) = parser.parse_args()

with open(options.config_file) as f:
  input = json.loads(f.readline())
parameters = input['parameters']

s3_fq1 = options.fq1
s3_fq2 = options.fq2
fq1 = os.path.join('/mnt/', os.path.basename(s3_fq1))
fq2 = os.path.join('/mnt2/', os.path.basename(s3_fq2))

ref = options.reference
platform = options.platform
sample = options.sample
threads = options.threads

file_root = os.path.basename(fq1)
sam = fq1 + '.sam'
rg_bam = fq1 + '.rg.bam'
bam = fq1 + '.raw.bam'
sorted_bam = options.output + file_root + '.sorted.bam'
sorted_bam_prefix = options.output + file_root + '.sorted'

try:
  if s3_fq1 == s3_fq2:
    temp_bam = fq1
    #command = "s3cmd -c /mydata/.s3cfg get %s %s" % (s3_fq1, temp_bam)
    for i in range(3):
      command = 'timelimit -t 86400 -T 1 aria2c -s16 -x16 -d /mnt/ "%s"' % (s3_signed_url(parameters, '/'.join(s3_fq1.split('/')[3:])))
      stat, stdout = commands.getstatusoutput(command)
      print stat, stdout
      if not stat:
        break
    temp_bam_sorted = fq1 + '.sorted'
    #sort_command = '%s sort -no -@ 8 -m 6G %s %s' % (samtools_mt_binary, temp_bam, temp_bam_sorted)
    sort_command = '%s sort -n -m 35000000000 %s %s' % (samtools_binary, temp_bam, temp_bam_sorted)
    for i in range(3):
      print "Attempt: %s" % i
      stat, stdout = commands.getstatusoutput(sort_command)
      print stat, stdout
      if not stat:
        break
    open(temp_bam, 'w').close()
    temp_bam_sorted += '.bam'
    fq1 += '.fq'
    fq2 += '.fq'
    convert = 'java -Xmx6g -jar %s I=%s F=%s F2=%s' % (picard_convert_binary, temp_bam_sorted, fq1, fq2)
    stdout = commands.getoutput(convert)
    open(temp_bam_sorted, 'w').close()
    print stdout
  else:
    #get_command1 = "s3cmd -c /mydata/.s3cfg get %s " % (s3_fq1)
    #get_command2 = "s3cmd -c /mydata/.s3cfg get %s " % (s3_fq2)
    
    for i in range(3):
      get_command1 = 'timelimit -t 86400 -T 1 aria2c -s8 -x8 -d /mnt/ "%s"' % (s3_signed_url(parameters, '/'.join(s3_fq1.split('/')[3:])))
      print get_command1
      
      stat, stdout = commands.getstatusoutput(get_command1)
      print stat, stdout
      if not stat:
        break
      
    for i in range(3):
      get_command2 = 'timelimit -t 86400 -T 1 aria2c -s8 -x8 -d /mnt2/ "%s"' % (s3_signed_url(parameters, '/'.join(s3_fq2.split('/')[3:])))
      stat, stdout = commands.getstatusoutput(get_command2)
      print stat, stdout
      if not stat:
        break
    
    # 1. Unzip files if zipped
    if fq1.endswith('.gz'):
      get_command1 = 'gzip -d %s' % fq1
      get_command2 = 'gzip -d %s' % fq2
      
      fq1 = os.path.splitext(fq1)[0]
      fq2 = os.path.splitext(fq2)[0]
      
      get1 = Process(target=commands.getstatusoutput, args=(get_command1, ))
      get1.start()
      
      get2 = Process(target=commands.getstatusoutput, args=(get_command2, ))
      get2.start()
      
      get1.join()
      get2.join()
  
  exit_status, stdout = commands.getstatusoutput('sudo sysctl vm.overcommit_memory=1')
  
  read_group_id = file_root
  exit_status, stdout = commands.getstatusoutput('touch %s/%s.sam' % (options.output, file_root))
  
  # 2. Align
  exit_status, stdout = commands.getstatusoutput('%s paired %s %s %s -o %s -t %s -b' % (snap_binary, ref, fq1, fq2, sam, threads))
  print exit_status, stdout
  exit_status, stdout = commands.getstatusoutput('touch %s/%s.raw.bam' % (options.output, file_root))
  
  # 3. SAM to BAM
  run_jobs = []
  for i in range(threads):
    thread_sam = re.sub('.sam$', '_%02d.sam' % i, sam)
    thread_bam = re.sub('.sam$', '.bam', thread_sam)
    # SNAP is not properly changing read names, have to edit for now
    edit_command = "perl -p -e 's/^(\S+)\/[12](\s)/$1$2/' %s" % thread_sam
    command = '%s view -b -h -S -t %s -o %s -' % (samtools_binary, ref, thread_bam)
    job = Process(target=commands.getstatusoutput, args=(edit_command + ' | ' + command,))
    job.start()
    run_jobs.append(job)
  
  [job.join() for job in run_jobs]
  
  # Reformat header
  run_jobs = []
  thread_bams = []
  for i in range(threads):
    thread_sam = re.sub('.sam$', '_%02d.sam' % i, sam)
    thread_bam = re.sub('.sam$', '_%02d.bam' % i, sam)
    thread_rg_bam = re.sub('.bam$', '.rg.bam', thread_bam)
    open(thread_sam, 'w').close()
    command = 'java -Xmx5g -jar %s INPUT=%s OUTPUT=%s SORT_ORDER=unsorted VALIDATION_STRINGENCY=SILENT' % (picard_rg_binary, thread_bam, thread_rg_bam)
    command += ' RGID=%s RGLB=%s RGPL=%s RGPU=%s RGSM=%s' % (read_group_id, sample, platform, 1, sample)
    print command
    job = Process(target=commands.getstatusoutput, args=(command,))
    job.start()
    run_jobs.append(job)
    thread_bams.append(thread_rg_bam)
  
  [job.join() for job in run_jobs]
  
  for thread_rg_bam in thread_bams:
    thread_bam = re.sub('.rg.bam$', '.bam', thread_rg_bam)
    open(thread_bam, 'w').close()
  
  # Cat
  exit_status, stdout = commands.getstatusoutput('%s cat -o %s %s' % (samtools_binary, rg_bam, ' '.join(thread_bams)))
  
  for thread_rg_bam in thread_bams:
    open(thread_rg_bam, 'w').close()
    
  # 4. Sort BAM
  exit_status, stdout = commands.getstatusoutput('%s sort %s %s' % (samtools_binary, rg_bam, sorted_bam_prefix))
  print exit_status, stdout
  
  exit_status, stdout = commands.getstatusoutput('touch %s.done' % (sorted_bam))
  print exit_status, stdout
except Exception, e:
  print >> sys.stderr, e
import sys
import os
import subprocess
import json
from optparse import OptionParser
import commands, subprocess
from multiprocessing import Process
from helpers import *

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--fq1', help='FASTQ file, pair 1')
parser.add_option('--fq2', help='FASTQ file, pair 2')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--platform', help='Platform', default='Illumina')
parser.add_option('--sample', help='Sample', default='Me')
parser.add_option('--quality', help='Quality', default='20')
parser.add_option('--output', help='Output directory')
parser.add_option('--config_file', help='Config File (JSON)')

(options, args) = parser.parse_args()

with open(options.config_file) as f:
  input = json.loads(f.readline())
parameters = input['parameters']

# Get files from S3
s3_fq1 = options.fq1
s3_fq2 = options.fq2
fq1 = os.path.join('/mnt/', os.path.basename(s3_fq1))
fq2 = os.path.join('/mnt2/', os.path.basename(s3_fq2))

ref = options.reference
platform = options.platform
sample = options.sample
quality = options.quality

bwa_binary = '%s/bwa' % root
samtools_binary = '%s/samtools' % root
picard_convert_binary = '%s/picard/SamToFastq.jar' % root

file_root = os.path.basename(fq1)
sai1 = fq1 + '.sai'
sai2 = fq2 + '_2.sai' if fq2.endswith('.bam') else fq2 + '.sai'
sam = fq1 + '.sam'
bam = fq1 + '.raw.bam'
sorted_bam = options.output + file_root + '.sorted.bam'
sorted_bam_prefix = options.output + file_root + '.sorted'

try:
  if s3_fq1 == s3_fq2:
    temp_bam = fq1
    #command = "s3cmd -c /mydata/.s3cfg get %s %s" % (s3_fq1, temp_bam)
    for i in range(3):
      command = 'timelimit -t 86400 -T 1 aria2c -V -s16 -x16 -d /mnt/ "%s"' % (s3_signed_url(parameters, '/'.join(s3_fq1.split('/')[3:])))
      stat, stdout = commands.getstatusoutput(command)
      print stat, stdout
      if not stat:
        break
    temp_bam_sorted = fq1 + '.sorted'
    #sort_command = '%s sort -no -@ 8 -m 6G %s %s' % (samtools_mt_binary, temp_bam, temp_bam_sorted)
    sort_command = '%s sort -n -m 35000000000 %s %s' % (samtools_binary, temp_bam, temp_bam_sorted)
    print sort_command
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
  
  rg_format = "\'@RG\\tID:%s\\tSM:%s\\tPL:%s\\tLB:%s\'" % (file_root, sample, platform, sample)
  
  # 1. ALN
  command = '%s aln -q %s -f %s %s %s' % (bwa_binary, quality, sai1, ref, fq1)
  aln1 = Process(target=commands.getstatusoutput, args=(command, ))
  aln1.start()
  
  command = '%s aln -q %s -f %s %s %s' % (bwa_binary, quality, sai2, ref, fq2)
  aln2 = Process(target=commands.getstatusoutput, args=(command, ))
  aln2.start()
  
  aln1.join()
  aln2.join()
  
  # 2. SAMPE
  open(options.output + file_root + '.sam', 'w').close()
  sampe_command = '%s sampe -r %s %s' % (bwa_binary, rg_format, ' '.join([ref, sai1, sai2, fq1, fq2]))
  view_command = '%s view -b -h -S -t %s -o %s -' % (samtools_binary, ref, bam)
  exit_status, stdout = commands.getstatusoutput(sampe_command + ' | ' + view_command)
  print exit_status, stdout
  open(sai1, 'w').close()
  open(sai2, 'w').close()
  
  # 3. SAM to BAM
  open(options.output + file_root + '.raw.bam', 'w').close()
  #exit_status, stdout = commands.getstatusoutput(view_command)
  #print exit_status, stdout
  
  # 4. Sort BAM
  exit_status, stdout = commands.getstatusoutput('%s sort %s %s' % (samtools_binary, bam, sorted_bam_prefix))
  print exit_status, stdout
  open(sorted_bam + '.done', 'w').close()
except Exception, e:
  print >> sys.stderr, e
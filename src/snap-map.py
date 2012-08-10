import sys
import os
import re
from optparse import OptionParser
import commands, subprocess
from multiprocessing import Process
from helpers import *

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--fq1', help='FASTQ file, pair 1')
parser.add_option('--fq2', help='FASTQ file, pair 2')
parser.add_option('--reference', help='Genome index directory')
parser.add_option('--platform', help='Platform', default='Illumina')
parser.add_option('--sample', help='Sample', default='Me')
parser.add_option('--threads', help='Sample', default=6)
parser.add_option('--output', help='Output directory')

(options, args) = parser.parse_args()

s3_fq1 = options.fq1
s3_fq2 = options.fq2
fq1 = os.path.join('/mnt/', os.path.basename(s3_fq1))
fq2 = os.path.join('/mnt2/', os.path.basename(s3_fq2))

ref = options.reference
platform = options.platform
sample = options.sample
threads = options.threads

snap_binary = '%s/snap' % root
samtools_binary = '%s/samtools' % root
picard_binary = '%s/picard/AddOrReplaceReadGroups.jar' % root
picard_convert_binary = '%s/picard/SamToFastq.jar' % root

file_root = os.path.basename(fq1)
sam = fq1 + '.sam'
rg_bam = fq1 + '.rg.bam'
bam = fq1 + '.raw.bam'
sorted_bam = options.output + file_root + '.sorted.bam'
sorted_bam_prefix = options.output + file_root + '.sorted'

try:
  if s3_fq1 == s3_fq2:
    command = "s3cmd -c /mydata/.s3cfg get %s -" % (s3_fq1)
    fq1 += '.fq'
    fq2 += '.fq'
    convert = 'java -Xmx6g -jar %s I=/dev/stdin F=%s F2=%s' % (picard_convert_binary, fq1, fq2)
    stdout = commands.getoutput(command + ' | ' + convert)
  else:
    get_command1 = "s3cmd -c /mydata/.s3cfg get %s " % (s3_fq1)
    get_command2 = "s3cmd -c /mydata/.s3cfg get %s " % (s3_fq2)
    gzip = fq1.endswith('.gz')
    # 1. Unzip files if zipped
    if gzip:
      fq1 = os.path.splitext(fq1)[0]
      fq2 = os.path.splitext(fq2)[0]
      get_command1 += '- | gzip -d > %s' % fq1
      get_command2 += '- | gzip -d > %s' % fq2
    else:
      get_command1 += fq1
      get_command2 += fq2
    
    get1 = Process(target=commands.getstatusoutput, args=(get_command1, ))
    get1.start()
    
    get2 = Process(target=commands.getstatusoutput, args=(get_command2, ))
    get2.start()
    
    get1.join()
    get2.join()
  
  exit_status, stdout = commands.getstatusoutput('sudo sysctl vm.overcommit_memory=1')
  
  read_group_id = file_root
  
  # 2. Align
  exit_status, stdout = commands.getstatusoutput('%s paired %s %s %s -o %s -t %s -b' % (snap_binary, ref, fq1, fq2, sam, threads))
  print exit_status, stdout
  exit_status, stdout = commands.getstatusoutput('touch %s/%s.sam' % (options.output, file_root))
  
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
  exit_status, stdout = commands.getstatusoutput('touch %s/%s.raw.bam' % (options.output, file_root))
  
  # Reformat header
  run_jobs = []
  thread_bams = []
  for i in range(threads):
    thread_bam = re.sub('.sam$', '_%02d.bam' % i, sam)
    thread_rg_bam = re.sub('.bam$', '.rg.bam', thread_bam)
    command = 'java -Xmx5g -jar %s INPUT=%s OUTPUT=%s SORT_ORDER=unsorted VALIDATION_STRINGENCY=SILENT' % (picard_binary, thread_bam, thread_rg_bam)
    command += ' RGID=%s RGLB=%s RGPL=%s RGPU=%s RGSM=%s' % (read_group_id, sample, platform, 1, sample)
    print command
    job = Process(target=commands.getstatusoutput, args=(command,))
    job.start()
    run_jobs.append(job)
    thread_bams.append(thread_rg_bam)
  
  [job.join() for job in run_jobs]
  
  # Cat
  exit_status, stdout = commands.getstatusoutput('%s cat -o %s %s' % (samtools_binary, rg_bam, ' '.join(thread_bams)))
  
  # 4. Sort BAM
  exit_status, stdout = commands.getstatusoutput('%s sort %s %s' % (samtools_binary, rg_bam, sorted_bam_prefix))
  print exit_status, stdout
  
  exit_status, stdout = commands.getstatusoutput('touch %s.done' % (sorted_bam))
  print exit_status, stdout
except Exception, e:
  print >> sys.stderr, e
import sys
import os
import subprocess
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
parser.add_option('--output', help='Output directory')

(options, args) = parser.parse_args()

s3_fq1 = options.fq1
s3_fq2 = options.fq2
fq1 = os.path.join('/mnt/', os.path.basename(s3_fq1))
fq2 = os.path.join('/mnt/', os.path.basename(s3_fq2))
stdout = commands.getoutput("s3cmd -c /mydata/.s3cfg get %s %s" % (s3_fq1, fq1))
if s3_fq1 != s3_fq2:
  stdout = commands.getoutput("s3cmd -c /mydata/.s3cfg get %s %s" % (s3_fq2, fq2))

ref = options.reference
platform = options.platform
sample = options.sample

snap_binary = '%s/snap' % root
samtools_binary = '%s/samtools' % root
picard_binary = '%s/picard/AddOrReplaceReadGroups.jar' % root

file_root = os.path.basename(fq1)
sai1 = fq1 + '.sai'
sai2 = fq2 + '.sai'
sam = fq1 + '.sam'
rg_bam = fq1 + '.rg.bam'
bam = fq1 + '.raw.bam'
sorted_bam = options.output + file_root + '.sorted.bam'
sorted_bam_prefix = options.output + file_root + '.sorted'

gzip = fq1.endswith('.gz')
# 1. Unzip files if zipped
if gzip:
  gz1 = Process(target=commands.getstatusoutput, args=('gzip -d %s' % fq1,))
  gz1.start()
  
  gz2 = Process(target=commands.getstatusoutput, args=('gzip -d %s' % fq2,))
  gz2.start()
  
  gz1.join()
  gz2.join()

  fq1 = os.path.splitext(fq1)[0]
  fq2 = os.path.splitext(fq2)[0]

read_group_id = file_root

# 2. SAMPE
exit_status, stdout = commands.getstatusoutput('%s paired %s %s %s -o %s' % (snap_binary, ref, fq1, fq2, sam))
print exit_status, stdout

if gzip:
  p = subprocess.Popen(['gzip', fq1], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
  print '%s\n' % p.pid
  
  p = subprocess.Popen(['gzip', fq2], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
  print '%s\n' % p.pid  

# 3. SAM to BAM
exit_status, stdout = commands.getstatusoutput('%s view -b -h -S -t %s -o %s %s' % (samtools_binary, ref, bam, sam))
print exit_status, stdout

command = 'java -Xmx5g -jar %s INPUT=%s OUTPUT=%s SORT_ORDER=unsorted' % (picard_binary, bam, rg_bam)
command += ' RGID=%s RGLB=%s RGPL=%s RGPU=%s RGSM=%s' % (read_group_id, sample, platform, 1, sample)
exit_status, stdout = commands.getstatusoutput(command)
print exit_status, stdout

# 4. Sort BAM
exit_status, stdout = commands.getstatusoutput('%s sort %s %s' % (samtools_binary, rg_bam, sorted_bam_prefix))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (sorted_bam))
print exit_status, stdout

import sys
import os
import subprocess
from optparse import OptionParser
import commands
from multiprocessing import Process

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--fq1', help='FASTQ file, pair 1')
parser.add_option('--fq2', help='FASTQ file, pair 2')
parser.add_option('--reference', help='Genome index directory')
parser.add_option('--platform', help='Platform', default='Illumina')
parser.add_option('--sample', help='Sample', default='Me')

(options, args) = parser.parse_args()

fq1 = options.fq1
fq2 = options.fq2
ref = options.reference
platform = options.platform
sample = options.sample

snap_binary = '%s/snap' % root
samtools_binary = '%s/samtools' % root

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

sam = fq1.replace('_1.fq', '.sam')
bam = sam.replace('.sam', '.raw.bam')
sorted_bam = bam.replace('.raw.bam', '.sorted.bam')
sorted_bam_prefix = sorted_bam.replace('.bam', '')

read_group_id = sam.replace('.sam', '')
rg_format = "\'@RG\\tID:%s\\tSM:%s\\tPL:%s\\tLB:%s\'" % (read_group_id, sample, platform, sample)

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
# 4. Sort BAM
exit_status, stdout = commands.getstatusoutput('%s sort %s %s' % (samtools_binary, bam, sorted_bam_prefix))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (sorted_bam))
print exit_status, stdout

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
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--platform', help='Platform', default='Illumina')
parser.add_option('--sample', help='Sample', default='Me')
parser.add_option('--quality', help='Quality', default='20')

(options,args) = parser.parse_args()

fq1 = options.fq1
fq2 = options.fq2
ref = options.reference
platform = options.platform
sample = options.sample
quality = options.quality

sai1 = fq1.replace('.fq.gz', '.sai').replace('.fq', '.sai')
sai2 = fq2.replace('.fq.gz', '.sai').replace('.fq', '.sai')
sam = sai1.replace('_1.sai', '.sam')
bam = sam.replace('.sam', '.raw.bam')
sorted_bam = bam.replace('.raw.bam', '.sorted.bam')
sorted_bam_prefix = sorted_bam.replace('.bam', '')

read_group_id = sam.replace('.sam', '')
rg_format = "\'@RG\\tID:%s\\tSM:%s\\tPL:%s\\tLB:%s\'" % (read_group_id, sample, platform, sample)

bwa_binary = '%s/bwa' % root
samtools_binary = '%s/samtools' % root

# 1. ALN
aln1 = Process(target=commands.getstatusoutput, args=('%s aln -q %s -f %s %s %s' % (bwa_binary, quality, sai1, ref, fq1), ))
aln1.start()

aln2 = Process(target=commands.getstatusoutput, args=('%s aln -q %s -f %s %s %s' % (bwa_binary, quality, sai2, ref, fq2), ))
aln2.start()

aln1.join()
aln2.join()

# 2. SAMPE
exit_status, stdout = commands.getstatusoutput('%s sampe -r %s -f %s' % (bwa_binary, rg_format, ' '.join([sam, ref, sai1, sai2, fq1, fq2])))
print exit_status, stdout

# 3. SAM to BAM
exit_status, stdout = commands.getstatusoutput('%s view -b -h -S -t %s -o %s %s' % (samtools_binary, ref, bam, sam))
print exit_status, stdout
# 4. Sort BAM
exit_status, stdout = commands.getstatusoutput('%s sort %s %s' % (samtools_binary, bam, sorted_bam_prefix))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (sorted_bam))
print exit_status, stdout

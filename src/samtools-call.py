import sys
import os
import subprocess
from optparse import OptionParser
import commands
import re
from helpers import *

parser = OptionParser()
parser.add_option('--bam', help='Input (cleaned) BAM file')
parser.add_option('--dbsnp', help='dbSNP VCF file')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--chromosome', help='Chromosome')
parser.add_option('--call_all_dbsnp', action="store_true", help='Call ALL sites in dbSNP as well as novel variants', default=False)
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)
parser.add_option('--indels', action='store_true', help='Call indels instead of SNPs', default=False)
parser.add_option('--opt_d', help='Max depth to call a variant', default=100)

(options, args) = parser.parse_args()

in_bam = options.bam
dbsnp = options.dbsnp
ref = options.reference
chromosome = options.chromosome

recal_bam = re.sub('.merged.bam$', '_%s.recal.bam' % chromosome, options.bam)
vcf = re.sub('.merged.bam$', '_%s.raw.vcf' % chromosome, options.bam)
bcf = re.sub('.vcf$', '.bcf', vcf)

command = '%s mpileup -uf %s %s | %s view -vcg - | %s varFilter -D %s > %s' % (samtools_binary, ref, recal_bam, bcftools_binary, vcfutils_binary, options.opt_d, vcf)
print command
exit_status, stdout = commands.getstatusoutput(command)
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (vcf))
print exit_status, stdout
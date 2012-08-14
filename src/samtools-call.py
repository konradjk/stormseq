import sys
import os
import subprocess
from optparse import OptionParser
import commands
import re

root = '/usr/local/bin'

parser = OptionParser()
parser.add_option('--bam', help='Input (cleaned) BAM file')
parser.add_option('--dbsnp', help='dbSNP VCF file')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--chromosome', help='Chromosome')
parser.add_option('--call_all_dbsnp', action="store_true", help='Call ALL sites in dbSNP as well as novel variants', default=False)
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)
parser.add_option('--indels', action='store_true', help='Call indels instead of SNPs', default=False)

(options, args) = parser.parse_args()

in_bam = options.bam
dbsnp = options.dbsnp
ref = options.reference
chromosome = options.chromosome

gatk_options = '-stand_call_conf %s -stand_emit_conf %s' % (options.stand_call_conf, options.stand_emit_conf)

chrom_bam = re.sub('.merged.bam$', '_%s.merged.bam' % chromosome, in_bam)
recal_bam = re.sub('.merged.bam$', '.recal.bam', chrom_bam)
vcf = re.sub('.merged.bam$', '', chrom_bam)
vcf += '.indel.vcf' if options.indels else '.vcf'
dbsnp_chr = dbsnp.replace('.vcf', '_%s.vcf' % chromosome)

gatk_binary = '%s/gatk/GenomeAnalysisTK.jar' % root

def run_gatk_commands(command):
  command += '' if options.intervals is None else ' -L %s' % options.intervals
  command += '' if options.intervals is None or command.find('--interval_set_rule INTERSECTION') > -1 else ' --interval_set_rule INTERSECTION'
  command += ' --genotype_likelihoods_model INDEL' if options.indels else ''
  print command
  exit_status, stdout = commands.getstatusoutput(command)
  print exit_status, stdout

if options.call_all_dbsnp:
  pass # bcftools -l
  raw_vcf = vcf.replace('.vcf', '.raw.vcf')
  command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper -L %s -R %s -I %s -o %s --dbsnp %s %s' % (gatk_binary, chromosome, ref, recal_bam, raw_vcf, dbsnp, gatk_options)
  run_gatk_commands(command)

  orig_dbsnp_vcf = vcf.replace('.vcf', '.dbsnp.all.vcf')
  command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper --dbsnp %s --output_mode EMIT_ALL_SITES --interval_set_rule INTERSECTION -L %s -L %s -R %s -I %s -o %s %s' % (gatk_binary, dbsnp, dbsnp_chr, chromosome, ref, recal_bam, orig_dbsnp_vcf, gatk_options)
  command += ' --genotyping_mode GENOTYPE_GIVEN_ALLELES --alleles %s' % dbsnp_chr
  run_gatk_commands(command)
  
  dbsnp_vcf = vcf.replace('.vcf', '.dbsnp.vcf')
  command = 'grep -vP "\.\/\." %s > %s' % (orig_dbsnp_vcf, dbsnp_vcf)
  exit_status, stdout = commands.getstatusoutput(command)
  print exit_status, stdout
  
  command = 'java -Xmx6500m -jar %s -T CombineVariants -R %s --variant:raw %s --variant:db %s -o %s -priority raw,db --genotypemergeoption UNSORTED --assumeIdenticalSamples' % (gatk_binary, options.reference, raw_vcf, dbsnp_vcf, vcf)
  run_gatk_commands(command)
else:
  pass

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (vcf))
print exit_status, stdout
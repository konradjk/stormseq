import sys
import os
import subprocess
from optparse import OptionParser
from multiprocessing import Process
import commands
import re
import boto

root = '/usr/local/bin'

parser = OptionParser()
parser.add_option('--bam', help='Input (merged) BAM file')
parser.add_option('--dbsnp', help='dbSNP VCF file')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--chromosome', help='Chromosome')
parser.add_option('--stand_call_conf', help='Standard min confidence threshold for calling', default='30.0')
parser.add_option('--stand_emit_conf', help='Standard min confidence threshold for emitting', default='30.0')
parser.add_option('--output_gvcf', action="store_true", help='Call ALL sites in dbSNP as well as novel variants', default=False)
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)
parser.add_option('--indels', action='store_true', help='Call indels in addition to of SNPs', default=False)

(options, args) = parser.parse_args()

gatk_binary = '%s/GenomeAnalysisTKLite-2.1-12-g2d7797a/GenomeAnalysisTKLite.jar' % root
samtools_binary = '%s/samtools' % root

dbsnp = options.dbsnp
ref = options.reference
chromosome = options.chromosome
dbsnp_chr = dbsnp.replace('.vcf', '_%s.vcf' % chromosome)
gatk_options = '-stand_call_conf %s -stand_emit_conf %s' % (options.stand_call_conf, options.stand_emit_conf)

recal_bam = '-I ' + re.sub('.merged.bam$', '_%s.recal.bam' % chromosome, options.bam)
vcf = re.sub('.merged.bam$', '_%s.vcf' % chromosome, options.bam)

def run_gatk_commands(command):
  command += '' if options.intervals is None else ' -L %s' % options.intervals
  command += '' if options.intervals is None or command.find('--interval_set_rule INTERSECTION') > -1 else ' --interval_set_rule INTERSECTION'
  print command
  exit_status, stdout = commands.getstatusoutput(command)
  print exit_status, stdout
  
def run_ug_commands(command):
  command += ' --genotype_likelihoods_model BOTH' if options.indels else ''
  run_gatk_commands(command)

try:
  if options.output_gvcf:
    #raw_vcf = vcf.replace('.vcf', '.raw.vcf')
    #command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper -L %s -R %s %s -o %s --dbsnp %s %s' % (gatk_binary, chromosome, ref, recal_bam, raw_vcf, dbsnp, gatk_options)
    #run_ug_commands(command)
    #
    #orig_dbsnp_vcf = vcf.replace('.vcf', '.dbsnp.all.vcf')
    #command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper --dbsnp %s --output_mode EMIT_ALL_SITES --interval_set_rule INTERSECTION -L %s -L %s -R %s %s -o %s %s' % (gatk_binary, dbsnp, dbsnp_chr, chromosome, ref, recal_bam, orig_dbsnp_vcf, gatk_options)
    #command += ' --genotyping_mode GENOTYPE_GIVEN_ALLELES --alleles %s' % dbsnp_chr
    command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper --dbsnp %s --output_mode EMIT_ALL_SITES -L %s -R %s %s %s | gatk_to_gvcf > %s' % (gatk_binary, dbsnp, chromosome, ref, recal_bam, gatk_options, vcf)
    run_ug_commands(command)
    
    #dbsnp_vcf = vcf.replace('.vcf', '.dbsnp.vcf')
    #command = 'grep -vP "\.\/\." %s > %s' % (orig_dbsnp_vcf, dbsnp_vcf)
    #exit_status, stdout = commands.getstatusoutput(command)
    #print exit_status, stdout
    #
    #command = 'java -Xmx6500m -jar %s -T CombineVariants -R %s --variant:raw %s --variant:db %s -o %s -priority raw,db --genotypemergeoption UNSORTED --assumeIdenticalSamples' % (gatk_binary, options.reference, raw_vcf, dbsnp_vcf, vcf)
    #run_gatk_commands(command)
  else:
    command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper -L %s -R %s %s -o %s --dbsnp %s %s' % (gatk_binary, chromosome, ref, recal_bam, vcf, dbsnp, gatk_options)
    run_ug_commands(command)
  
  exit_status, stdout = commands.getstatusoutput('touch %s.done' % (vcf))
  print exit_status, stdout
except Exception, e:
  print >> sys.stderr, e
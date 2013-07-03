import sys
import os
import subprocess
from optparse import OptionParser
import commands
import re
from helpers import *

parser = OptionParser()
parser.add_option('--bam', help='Input (sorted) BAM file')
parser.add_option('--dbsnp', help='dbSNP VCF file')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--chromosome', help='Chromosome')
parser.add_option('--platform', help='Platform', default='Illumina')
#parser.add_option('--covariates', help='Covariates (comma-separated)', default='ReadGroupCovariate,QualityScoreCovariate,CycleCovariate,DinucCovariate,HomopolymerCovariate') #1.6
parser.add_option('--covariates', help='Covariates (comma-separated)', default='ReadGroupCovariate,QualityScoreCovariate,CycleCovariate,ContextCovariate')
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)
parser.add_option('--bad_cigar', help='Allow malformed CIGAR strings (recommended for SNAP)', action='store_true', default=False)

(options,args) = parser.parse_args()
print options
in_bam = options.bam
dbsnp = options.dbsnp
ref = options.reference
chromosome = options.chromosome
platform = options.platform
covariates_raw = options.covariates
covariates = ' '.join(['-cov ' + x for x in covariates_raw.split(',')])

chrom_bam = re.sub('.merged.bam$', '_%s.merged.bam' % chromosome, in_bam)
nodup_bam = re.sub('.merged.bam$', '.nodup.bam', chrom_bam)
dup_met = re.sub('.merged.bam$', '.dupmetrics', chrom_bam)
realign_intervals = re.sub('.merged.bam$', '.realigner.intervals', chrom_bam)
realigned_bam = re.sub('.merged.bam$', '.align.bam', chrom_bam)
rec_file = re.sub('.merged.bam$', '.recal_data.cov', chrom_bam)
recal_bam = re.sub('.merged.bam$', '.recal.bam', chrom_bam)
vcf = re.sub('.merged.bam$', '.vcf', chrom_bam)

try:
  # Split by chromosome
  command = '%s view -b -h -o %s %s %s' % (samtools_binary, chrom_bam, in_bam, chromosome)
  exit_status, stdout = commands.getstatusoutput(command)
  print exit_status, stdout
  
  # 5. Mark Dups
  command = 'java -Xmx4g -jar %s I=%s O=%s M=%s AS=true REMOVE_DUPLICATES=false VALIDATION_STRINGENCY=SILENT CREATE_INDEX=true' % (picard_binary, chrom_bam, nodup_bam, dup_met)
  exit_status, stdout = commands.getstatusoutput(command)
  print exit_status, stdout
  open(chrom_bam, 'w').close()
  
  def run_gatk_commands(command):
    command += '' if options.intervals is None else ' --interval_set_rule INTERSECTION -L %s' % options.intervals
    print command
    exit_status, stdout = commands.getstatusoutput(command)
    print exit_status, stdout
  
  # 6. Find regions to realign
  command = 'java -Xmx6g -jar %s -T RealignerTargetCreator -L %s -R %s -I %s --known %s -o %s' % (gatk_binary, chromosome, ref, nodup_bam, dbsnp, realign_intervals)
  run_gatk_commands(command)
  
  # 7. Indel realignment
  command = 'java -Xmx6g -jar %s -T IndelRealigner -L %s -R %s -I %s -o %s --knownAlleles %s --targetIntervals %s' % (gatk_binary, chromosome, ref, nodup_bam, realigned_bam, dbsnp, realign_intervals)
  run_gatk_commands(command)
  open(nodup_bam, 'w').close()
  
  # 8. Count Covariates
  #command = 'java -Xmx6g -jar %s -T CountCovariates %s -L %s -R %s -I %s --knownSites %s --default_platform %s -recalFile %s' % (gatk_binary, covariates, chromosome, ref, realigned_bam, dbsnp, platform, rec_file) # 1.6
  command = 'java -Xmx6g -jar %s -T BaseRecalibrator %s -L %s -R %s -I %s --knownSites %s --default_platform %s -o %s --disable_indel_quals' % (gatk_binary, covariates, chromosome, ref, realigned_bam, dbsnp, platform, rec_file)
  command += ' -rf BadCigar' if options.bad_cigar else ''
  run_gatk_commands(command)
  
  # 9. Base Quality Score Recalibration
  command = 'java -Xmx6g -jar %s -T PrintReads -L %s -R %s -I %s --out %s -BQSR %s' % (gatk_binary, chromosome, ref, realigned_bam, recal_bam, rec_file)
  command += ' -rf BadCigar' if options.bad_cigar else ''
  run_gatk_commands(command)
  open(realigned_bam, 'w').close()

except Exception, e:
  print >> sys.stderr, e
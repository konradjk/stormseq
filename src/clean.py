import sys
import os
import subprocess
from optparse import OptionParser
import commands

root = '/usr/local/bin'

parser = OptionParser()
parser.add_option('--bam', help='Input (sorted) BAM file')
parser.add_option('--dbsnp', help='dbSNP VCF file')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--chromosome', help='Chromosome')
parser.add_option('--platform', help='Platform', default='Illumina')
parser.add_option('--covariates', help='Covariates (comma-separated)', default='ReadGroupCovariate,QualityScoreCovariate,CycleCovariate,DinucCovariate,HomopolymerCovariate')
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)

(options,args) = parser.parse_args()
print options
in_bam = options.bam
dbsnp = options.dbsnp
ref = options.reference
chromosome = options.chromosome
platform = options.platform
covariates_raw = options.covariates
covariates = ' '.join(['-cov ' + x for x in covariates_raw.split(',')])

chrom_bam = in_bam.replace('.merged.bam', '_%s.merged.bam' % chromosome)
nodup_bam = chrom_bam.replace('.merged.bam', '.nodup.bam')
dup_met = chrom_bam.replace('.merged.bam', '.dupmetrics')
realign_intervals = chrom_bam.replace('.merged.bam', '.realigner.intervals')
realigned_bam = chrom_bam.replace('.merged.bam', '.align.bam')
rec_file = chrom_bam.replace('.merged.bam', '.recal_data.csv')
recal_bam = chrom_bam.replace('.merged.bam', '.recal.bam')
vcf = chrom_bam.replace('.merged.bam', '.vcf')

bwa_binary = '%s/bwa' % root
samtools_binary = '%s/samtools' % root
picard_binary = '%s/picard/MarkDuplicates.jar' % root
gatk_binary = '%s/gatk/GenomeAnalysisTK.jar' % root


# Split by chromosome
command = '%s view -b -h -o %s %s %s' % (samtools_binary, chrom_bam, in_bam, chromosome)
exit_status, stdout = commands.getstatusoutput(command)
print exit_status, stdout

# 5. Mark Dups
command = 'java -Xmx4g -jar %s I=%s O=%s M=%s AS=true REMOVE_DUPLICATES=false VALIDATION_STRINGENCY=SILENT CREATE_INDEX=true' % (picard_binary, chrom_bam, nodup_bam, dup_met)
exit_status, stdout = commands.getstatusoutput(command)
print exit_status, stdout

def run_gatk_commands(command):
  command += '' if options.intervals is None else ' --interval_set_rule INTERSECTION -L %s' % options.intervals
  print command
  exit_status, stdout = commands.getstatusoutput(command)
  print exit_status, stdout

# 6. Find regions to realign
command = 'java -Xmx4g -jar %s -T RealignerTargetCreator -L %s -R %s -I %s -o %s' % (gatk_binary, chromosome, ref, nodup_bam, realign_intervals)
run_gatk_commands(command)

# 7. Indel realignment
command = 'java -Xmx6g -jar %s -T IndelRealigner -L %s -R %s -I %s -o %s --targetIntervals %s' % (gatk_binary, chromosome, ref, nodup_bam, realigned_bam, realign_intervals)
run_gatk_commands(command)

# 8. Count Covariates
command = 'java -Xmx4g -jar %s -T CountCovariates %s -L %s -R %s -I %s --knownSites %s --default_platform %s -recalFile %s' % (gatk_binary, covariates, chromosome, ref, realigned_bam, dbsnp, platform, rec_file)
run_gatk_commands(command)

# 9. Base Quality Score Recalibration
command = 'java -Xmx4g -jar %s -T TableRecalibration -L %s -R %s -I %s --out %s --default_platform %s -recalFile %s' % (gatk_binary, chromosome, ref, realigned_bam, recal_bam, platform, rec_file)
run_gatk_commands(command)
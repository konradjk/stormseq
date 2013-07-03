import sys
import os
import json
import subprocess
from optparse import OptionParser
from multiprocessing import Process
import commands
import re
import boto
import urllib2
from helpers import *

parser = OptionParser()
parser.add_option('--samples', help='Input S3 filenames')
parser.add_option('--dbsnp', help='dbSNP VCF file')
parser.add_option('--reference', help='Genome FASTA file')
parser.add_option('--chromosome', help='Chromosome')
parser.add_option('--stand_call_conf', help='Standard min confidence threshold for calling', default='30.0')
parser.add_option('--stand_emit_conf', help='Standard min confidence threshold for emitting', default='30.0')
parser.add_option('--output_gvcf', action="store_true", help='Call ALL sites in dbSNP as well as novel variants', default=False)
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)
parser.add_option('--indels', action='store_true', help='Call indels instead of SNPs', default=False)
parser.add_option('--config_file', help='Config File (JSON)')

(options, args) = parser.parse_args()

with open(options.config_file) as f:
  input = json.loads(f.readline())
parameters = input['parameters']

def s3_signed_url(file_path):
  s3conn = boto.connect_s3(parameters['access_key_id'], parameters['secret_access_key'])
  bucket = s3conn.get_bucket(parameters['s3_bucket'], validate=False)
  key = bucket.new_key(file_path)
  signed_url = key.generate_url(expires_in=3600)
  return signed_url.replace('https://', 'http://')

dbsnp = options.dbsnp
ref = options.reference
chromosome = options.chromosome
dbsnp_chr = dbsnp.replace('.vcf', '_%s.vcf' % chromosome)
gatk_options = '-stand_call_conf %s -stand_emit_conf %s' % (options.stand_call_conf, options.stand_emit_conf)

input_bams = options.samples.split(',')

try:
  os.mkdir('/mnt/' + chromosome)
except OSError:
  pass

jobs = []
recal_bams = []
os.chdir('/mnt/' + chromosome)
for bam in input_bams:
  bai_url = s3_signed_url(bam.replace('.bam', '.bai'))
  bam_url = s3_signed_url(bam)
  bam_filename = os.path.join('/mnt/', chromosome, bam_url.split('/')[-1])
  with open(bam_filename + '.bai', 'wb') as bai_output:
    bai_file = urllib2.urlopen(bai_url)
    bai_output.write(bai_file.read())
  recal_bam = re.sub('.bam$', '_%s.bam' % chromosome, os.path.join('/mnt/', os.path.basename(bam)))
  command = '%s view -b -o %s "%s" %s;' % (samtools_binary, recal_bam, bam_url, chromosome)
  command += ' %s index %s' % (samtools_binary, recal_bam)
  print command
  job = Process(target=commands.getstatusoutput, args=(command,))
  job.start()
  jobs.append(job)
  recal_bams.append("-I " + recal_bam)
[job.join() for job in jobs]
recal_bam = " ".join(recal_bams)
vcf = '/mydata/stormseq_all_samples_%s.vcf' % chromosome

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
    command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper --dbsnp %s --output_mode EMIT_ALL_SITES -L %s -R %s %s %s | gatk_to_gvcf > %s' % (gatk_binary, dbsnp, chromosome, ref, recal_bam, gatk_options, vcf)
    run_ug_commands(command)
  else:
    command = 'java -Xmx6500m -jar %s -T UnifiedGenotyper -L %s -R %s %s -o %s --dbsnp %s %s' % (gatk_binary, chromosome, ref, recal_bam, vcf, dbsnp, gatk_options)
    run_ug_commands(command)
  
  exit_status, stdout = commands.getstatusoutput('touch %s.done' % (vcf))
  print exit_status, stdout
except Exception, e:
  print >> sys.stderr, e
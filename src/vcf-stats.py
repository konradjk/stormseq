import sys
import os
import subprocess
from optparse import OptionParser
import commands
import re

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--input', help='VCF file')
parser.add_option('--output')
parser.add_option('--reference')
parser.add_option('--dbsnp', default=None)
parser.add_option('--intervals', default=None)

(options, args) = parser.parse_args()

gatk_binary = '%s/gatk/GenomeAnalysisTK.jar' % root
vcftools_binary = '%s/vcftools' % root

sample = os.path.splitext(os.path.basename(options.input))[0]
other_options = '' if options.dbsnp is None else '--dbsnp %s' % options.dbsnp
other_options += '' if options.intervals is None else ' --intervals %s' % options.intervals

gatk_command = 'java -Xmx4g -jar %s -R %s -T VariantEval -o %s --eval:%s %s %s' % (gatk_binary, options.reference, options.output, sample, options.input, other_options)
print gatk_command
vcf_command = '%s --vcf %s --SNPdensity 1000000 --out %s' % (vcftools_binary, options.input, options.input)
print vcf_command

cmd1 = Process(target=commands.getstatusoutput, args=(gatk_command, ))
cmd1.start()
cmd2 = Process(target=commands.getstatusoutput, args=(vcf_command, ))
cmd2.start()

cmd1.join()
cmd2.join()

#exit_status, stdout = commands.getstatusoutput('tar zcv %s* > %s.tar.gz' % (options.output, options.output))
#print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
print exit_status, stdout
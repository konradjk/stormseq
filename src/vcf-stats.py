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

(options, args) = parser.parse_args()

gatk_binary = '%s/gatk/GenomeAnalysisTK.jar' % root

sample = os.path.splitext(os.path.basename(options.input))[0]
other_options = '' if options.dbsnp is None else '--dbsnp %s' % options.dbsnp

exit_status, stdout = commands.getstatusoutput('java -Xmx4g -jar %s -R %s -T VariantEval -o %s --eval:%s %s %s' % (gatk_binary, options.reference, options.output, sample, options.input, other_options))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('tar zcv %s* > %s.tar.gz' % (options.output, options.output))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
print exit_status, stdout
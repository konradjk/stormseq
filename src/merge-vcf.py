import sys
import os
import subprocess
from optparse import OptionParser
import commands
from multiprocessing import Process

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--output', help='Output file')
parser.add_option('--priority', help='Priority string for GATK')
parser.add_option('--reference', help='Reference')

(options,args) = parser.parse_args()

input = ' '.join(["--variant %s_%s.vcf" % (options.output.replace('.vcf', ''), chr) for chr in options.priority.split(',')])

gatk_binary = '%s/gatk/GenomeAnalysisTK.jar' % root

gatk_command = 'java -Xmx4g -jar %s -T CombineVariants -R %s %s -o %s --genotypemergeoption PRIORITIZE --assumeIdenticalSamples' % (gatk_binary, options.reference, input, options.output)
exit_status, stdout = commands.getstatusoutput(gatk_command)
print exit_status, stdout

#exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
#print exit_status, stdout
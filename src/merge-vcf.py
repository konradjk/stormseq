import sys
import os
import subprocess
from optparse import OptionParser
import commands
from multiprocessing import Process
from helpers import *

parser = OptionParser()
parser.add_option('--output', help='Output file')
parser.add_option('--priority', help='Priority string for GATK')
parser.add_option('--reference', help='Reference')
parser.add_option('--lite', help='Run GATK Lite instead of Full', action='store_true', default=False)

(options,args) = parser.parse_args()

if options.lite: gatk_binary = gatk_lite_binary

input = ' '.join(["--variant %s_%s.vcf" % (options.output.replace('.vcf', ''), chr) for chr in options.priority.split(',')])

gatk_command = 'java -Xmx4g -jar %s -T CombineVariants -R %s %s -o %s --genotypemergeoption UNSORTED --assumeIdenticalSamples' % (gatk_binary, options.reference, input, options.output)
exit_status, stdout = commands.getstatusoutput(gatk_command)
print exit_status, stdout

#exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
#print exit_status, stdout
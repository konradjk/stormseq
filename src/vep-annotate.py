import sys
import os
import subprocess
from optparse import OptionParser
from multiprocessing import Process
import commands
import re
from helpers import *

parser = OptionParser()
parser.add_option('--input', help='VCF file')
parser.add_option('--output')
parser.add_option('--chromosome')
parser.add_option('--threads', default=1)

(options, args) = parser.parse_args()

if options.chromosome in ('chrY', 'chrM'):
	vep_command = 'cp %s %s' % (options.input, options.output)
else:
	vep_command = 'perl %s --cache --offline --format vcf --vcf --regulatory --sift b --polyphen b --protein --numbers --domains -i %s -o %s' % (vep_binary, options.input, options.output)
	if options.threads > 1:
		vep_command += ' --fork %s' % options.threads
print vep_command
exit_status, stdout = commands.getstatusoutput(vep_command)
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
print exit_status, stdout
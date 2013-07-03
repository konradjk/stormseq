import sys
import os
import subprocess
from optparse import OptionParser
import commands
from multiprocessing import Process
from helpers import *

parser = OptionParser()
parser.add_option('--input', help='BAM file')
parser.add_option('--output')
parser.add_option('--reference')
parser.add_option('--intervals', help='Intervals file (for exome seq, e.g.)', default=None)
parser.add_option('--gene_list', default=None)

(options, args) = parser.parse_args()

other_options = '--omitDepthOutputAtEachBase --omitLocusTable'
other_options += '' if options.gene_list is None else ' --calculateCoverageOverGenes %s' % options.gene_list
other_options += '' if options.intervals is None else ' -L %s' % options.intervals

command = 'java -Xmx4g -jar %s -R %s -T DepthOfCoverage -o %s -I %s %s' % (gatk_binary, options.reference, options.output, options.input, other_options)
print command
exit_status, stdout = commands.getstatusoutput(command)
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('tar zcv %s* > %s.tar.gz' % (options.output, options.output))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
print exit_status, stdout
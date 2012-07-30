import sys
import os
import subprocess
from optparse import OptionParser
import commands
from multiprocessing import Process

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--input', help='BAM file')
parser.add_option('--output')
parser.add_option('--reference')
parser.add_option('--gene_list', default=None)

(options, args) = parser.parse_args()

gatk_binary = '%s/gatk/GenomeAnalysisTK.jar' % root
other_options = '--omitDepthOutputAtEachBase --omitLocusTable'
other_options += '--calculateCoverageOverGenes %s' % options.gene_list if options.gene_list is not None else ''

exit_status, stdout = commands.getstatusoutput('java -Xmx4g -jar %s -R %s -T DepthOfCoverage -o %s -I %s %s' % (gatk_binary, options.reference, options.output, options.input, other_options))
print exit_status, stdout
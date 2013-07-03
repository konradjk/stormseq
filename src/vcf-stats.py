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
parser.add_option('--reference')
parser.add_option('--dbsnp', default=None)
parser.add_option('--intervals', default=None)

(options, args) = parser.parse_args()

sample = os.path.splitext(os.path.basename(options.input))[0]
other_options = '' if options.dbsnp is None else '--dbsnp %s' % options.dbsnp
other_options += '' if options.intervals is None else ' --intervals %s' % options.intervals

# Start VariantEval since it's the slowest
gatk_command = 'java -Xmx4g -jar %s -R %s -T VariantEval -o %s --eval:%s %s %s' % (gatk_binary, options.reference, options.output, sample, options.input, other_options)
print gatk_command
cmd1 = Process(target=commands.getstatusoutput, args=(gatk_command, ))
cmd1.start()

# Start vcftools density and depth
vcf_command = '%s --vcf %s --SNPdensity 1000000 --site-depth --out %s' % (vcftools_binary, options.input, options.input)
print vcf_command
cmd2 = Process(target=commands.getstatusoutput, args=(vcf_command, ))
cmd2.start()

# Annotation summary stats
annotation_stats_command = 'python /root/annotation_stats.py --input %s --sample %s' % (options.input, sample)
cmd3 = Process(target=commands.getstatusoutput, args=(annotation_stats_command, ))
cmd3.start()

# When vcftools is done, plot density
cmd2.join()
plot_snp_density_command = '/root/plot_circos.R --sample %s' % sample
cmd4 = Process(target=commands.getstatusoutput, args=(plot_snp_density_command, ))
cmd4.start()

cmd1.join()
cmd3.join()
cmd4.join()

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
print exit_status, stdout
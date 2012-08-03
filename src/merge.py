import sys
import os
import time
import subprocess
from optparse import OptionParser
import commands
from multiprocessing import Process

root = '/usr/local/bin/'

parser = OptionParser()
parser.add_option('--bams', help='Sorted BAM files')
parser.add_option('--output', help='Sample', default='Me')

(options, args) = parser.parse_args()

input = ' '.join(["I=%s" % lane for lane in options.bams.split(',')])

stats_file = options.output.replace('.bam', '.stats')
picard_options = ['AS=TRUE', 'MAX_RECORDS_IN_RAM=2000000', 'VALIDATION_STRINGENCY=SILENT', 'CREATE_INDEX=true', 'MERGE_SEQUENCE_DICTIONARIES=true']
picard_merge_binary = '%s/picard/MergeSamFiles.jar' % root
picard_stats_binary = '%s/picard/CollectMultipleMetrics.jar' % root

exit_status, stdout = commands.getstatusoutput('java -Xmx4g -jar %s %s O=%s %s' % (picard_merge_binary, input, options.output, ' '.join(picard_options)))
print exit_status, stdout
for file in options.bams.split(','):
  open(file, 'w').close()

exit_status, stdout = commands.getstatusoutput('java -Xmx4g -jar %s I=%s O=%s VALIDATION_STRINGENCY=SILENT' % (picard_stats_binary, options.output, stats_file))
print exit_status, stdout

time.sleep(120)
exit_status, stdout = commands.getstatusoutput('tar zcv %s* > %s.tar.gz' % (stats_file, stats_file))
print exit_status, stdout

exit_status, stdout = commands.getstatusoutput('touch %s.done' % (options.output))
print exit_status, stdout
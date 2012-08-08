import time, json, sys, copy
import commands, subprocess
from helpers import *

config_file = sys.argv[1]
with open(config_file) as cnf:
  input = json.loads(cnf.readline())

files = input['files']
sample = input['sample']
parameters = input['parameters']
parameters['sample_name'] = sample
setup_s3cfg(parameters)

try:
  f = open("/tmp/final_log_%s.txt" % sample, "w")
  f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
  f.flush()
  
  time.sleep(300)
  check_command = "sudo starcluster sshmaster stormseq_%s 'qstat'" % sample
  es, stdout = commands.getstatusoutput(check_command)
  print stdout
  
  # Check for jobs being done
  files_to_get = ['mergef', 'depth', 'mergevs', 'vcfstats']
  
  file_dict = dict(zip(files_to_get, len(files_to_get)*[False]))
  while True:
      print file_dict
      if sum(file_dict.values()) == len(file_dict.keys()):
          break
      
      if not file_dict['mergef'] and stdout.find('mergef') == -1:
          print 'found %s.final.bam' % sample
          job, bucket_file = put_file_in_s3(sample, sample + '.final.bam', parameters['s3_bucket'], 1)
          print 'put submitted'
          touch_file(sample, job, sample + '.final.bam.done', f)
          print 'touched'
          
          print 'getting %s.final.stats.tar.gz'
          get_stats_file(sample, sample + '.final.stats.tar.gz', f)
          print 'putting file in s3'
          job, bucket_file = put_file_in_s3(sample, sample + '.final.stats.tar.gz', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.final.stats.tar.gz.done', f)
          
          file_dict['mergef'] = True
        
      if not file_dict['depth'] and stdout.find('depth') == -1:
          print 'found %s.depth' % sample
          get_stats_file(sample, sample + '.depth.tar.gz', f)
          job, bucket_file = put_file_in_s3(sample, sample + 'depth.tar.gz', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.depth.tar.gz.done', f)
          
          file_dict['depth'] = True
          
      if not file_dict['mergevs'] and stdout.find('mergevs') == -1:
          print 'found %s.vcf' % sample
          job, bucket_file = put_file_in_s3(sample, sample + '.vcf', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.vcf.done', f)
          
          file_dict['mergevs'] = True
          
      if not file_dict['vcfstats'] and stdout.find('vcfstats') == -1:
          print 'found %s.vcf.eval' % sample
          get_stats_file(sample, sample + '.vcf.eval', f)
          job, bucket_file = put_file_in_s3(sample, sample + '.vcf.eval', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.vcf.eval.done', f)
          
          file_dict['vcfstats'] = True
      
      print 'got here'
      time.sleep(10)
      es, stdout = commands.getstatusoutput(check_command)
      print stdout
  
  
  #exit_status, stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq_%s' % sample)
  #f.write(stdout + '\n')
  #
  #exit_status, stdout = commands.getstatusoutput('sudo starcluster removekey stormseq_starcluster_%s' % sample)
  #f.write(stdout + '\n')
  
  f.close()

except Exception, e:
  f.write('Error: %s\n' % e)
  sys.exit()
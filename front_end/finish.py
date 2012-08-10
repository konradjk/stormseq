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
  f.write('%s\n' % stdout)
  
  # Check for jobs being done
  files_to_get = ['mergef', 'depth', 'mergevs', 'vcfstats']
  
  file_dict = dict(zip(files_to_get, len(files_to_get)*[False]))
  nodes_removed = False
  while True:
      if stdout.find('python') == -1 and not nodes_removed:
          es, node_stdout = commands.getstatusoutput("starcluster lc stormseq_%s" % sample)
          nodes = [x.strip().split()[0] for x in node_stdout.split('\n') if x.strip().split()[0].startswith('node')]
          for node in nodes:
            if node == 'node001': continue
            try:
              es, node_stdout = commands.getstatusoutput("starcluster rn stormseq_%s %s" % (sample, node))
            except Exception, e:
              f.write('Could not shut down %s\nError:%s\n' % (node, str(e)))
          nodes_removed = True
      
      if sum(file_dict.values()) == len(file_dict.keys()):
          break
      
      if not file_dict['mergef'] and stdout.find('mergef') == -1:
          f.write('found %s.final.bam\n' % sample)
          job, bucket_file = put_file_in_s3(sample, sample + '.final.bam', parameters['s3_bucket'], 1)
          f.write('put submitted\n')
          touch_file(sample, job, sample + '.final.bam.done', f)
          f.write('touched\n')
          
          f.write('getting %s.final.stats.tar.gz\n' % sample)
          get_stats_file(sample, sample + '.final.stats.tar.gz', f)
          f.write('putting file in s3\n')
          job, bucket_file = put_file_in_s3(sample, sample + '.final.stats.tar.gz', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.final.stats.tar.gz.done', f)
          
          file_dict['mergef'] = True
        
      if not file_dict['depth'] and stdout.find('depth') == -1:
          f.write('found %s.depth\n' % sample)
          get_stats_file(sample, sample + '.depth.tar.gz', f)
          job, bucket_file = put_file_in_s3(sample, sample + '.depth.tar.gz', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.depth.tar.gz.done', f)
          
          file_dict['depth'] = True
          
      if not file_dict['mergevs'] and stdout.find('mergevs') == -1:
          f.write('found %s.vcf\n' % sample)
          job, bucket_file = put_file_in_s3(sample, sample + '.vcf', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.vcf.done', f)
          
          file_dict['mergevs'] = True
          
      if not file_dict['vcfstats'] and stdout.find('vcfstats') == -1:
          f.write('found %s.vcf.eval\n' % sample)
          get_stats_file(sample, sample + '.vcf.eval', f)
          job, bucket_file = put_file_in_s3(sample, sample + '.vcf.eval', parameters['s3_bucket'], 1)
          touch_file(sample, job, sample + '.vcf.eval.done', f)
          
          file_dict['vcfstats'] = True
      
      time.sleep(10)
      es, stdout = commands.getstatusoutput(check_command)
  
  
  exit_status, stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq_%s' % sample)
  f.write(stdout + '\n')
  
  exit_status, stdout = commands.getstatusoutput('sudo starcluster removekey stormseq_starcluster_%s' % sample)
  f.write(stdout + '\n')
  
  f.close()

except Exception, e:
  f.write('Error: %s\n' % e)
  sys.exit()
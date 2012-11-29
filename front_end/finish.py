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
  
  #put_conf_file_command = 'sudo starcluster put stormseq_%s /root/.boto /root/.boto' % (sample)
  #stdout = commands.getoutput(put_conf_file_command)
  #put_conf_file_command = 'sudo starcluster put stormseq_%s --node node001 /root/.boto /root/.boto' % (sample)
  #stdout = commands.getoutput(put_conf_file_command)
  # Check for jobs being done
  #files_to_get = ['mergef', 'mergefu', 'depth', 'mergevs', 'vcfstats']
  #file_dict = dict(zip(files_to_get, len(files_to_get)*[False]))
  #bam_upload_job = 0
  
  time.sleep(600)
  
  nodes_removed = False
  check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
  check_command.append("'qstat'")
  qstat_stdout = subprocess.check_output(check_command)
  f.write('%s\nlength: %s\n' % (qstat_stdout, len(qstat_stdout.split('\n'))))
  while len(qstat_stdout.split('\n')) > 5:
    time.sleep(300)
    try:
      qstat_stdout = subprocess.check_output(check_command)
    except Exception, e:
      f.write('Error in qstat: %s\n' % str(e))
      continue
    
    # Remove a bunch of nodes when most of the work is done to save on costs
    if not nodes_removed and qstat_stdout.find('python') == -1:
      f.write('Done most of the work. Removing nodes\n')
      es, node_stdout = commands.getstatusoutput("starcluster lc stormseq_%s" % sample)
      nodes = [x.strip().split()[0] for x in node_stdout.split('\n') if x.strip().startswith('node')]
      for node in nodes:
        if node == 'node001': continue
        try:
          es, node_stdout = commands.getstatusoutput("starcluster rn stormseq_%s %s" % (sample, node))
        except Exception, e:
          f.write('Could not shut down %s\nError:%s\n' % (node, str(e)))
      nodes_removed = True
    
    #all_jobs = [line.strip().split()[0] for line in qstat_stdout.split('\n') if line.find('root') > -1]
    #if sum(file_dict.values()) == len(file_dict.keys()) and len(qstat_stdout.split('\n')) <= 5:
    #    f.write('exiting with:\n%s\n' % qstat_stdout)
    #    break
    #      
    #if not file_dict['mergef'] and qstat_stdout.find('mergef') == -1:
    #    f.write(qstat_stdout + '\n')
    #    f.write('found %s.final.bam\n' % sample)
    #    job, bucket_file = put_file_in_s3(sample, sample + '.final.bai', parameters['s3_bucket'], 1)
    #    bam_upload_job, bucket_file = put_file_in_s3(sample, sample + '.final.bam', parameters['s3_bucket'], 1)
    #    f.write('put submitted (job %s)\n' % bam_upload_job)
    #    touch_file(sample, bam_upload_job, sample + '.final.bam.done', f)
    #    f.write('touched\n')
    #    
    #    f.write('getting %s.final.stats.tar.gz\n' % sample)
    #    get_stats_file(sample, sample + '.final.stats.tar.gz', f)
    #    f.write('putting file in s3\n')
    #    job, bucket_file = put_file_in_s3(sample, sample + '.final.stats.tar.gz', parameters['s3_bucket'], 1)
    #    touch_file(sample, job, sample + '.final.stats.tar.gz.done', f)
    #    
    #    file_dict['mergef'] = True
    #    
    #if not file_dict['depth'] and qstat_stdout.find('depth') == -1:
    #    f.write(qstat_stdout + '\n')
    #    f.write('found %s.depth\n' % sample)
    #    get_stats_file(sample, sample + '.depth.tar.gz', f)
    #    job, bucket_file = put_file_in_s3(sample, sample + '.depth.tar.gz', parameters['s3_bucket'], 1)
    #    touch_file(sample, job, sample + '.depth.tar.gz.done', f)
    #    
    #    file_dict['depth'] = True
    #    
    #if not file_dict['mergevs'] and qstat_stdout.find('mergevs') == -1:
    #    f.write(qstat_stdout + '\n')
    #    f.write('found %s.vcf\n' % sample)
    #    job, bucket_file = put_file_in_s3(sample, sample + '.vcf', parameters['s3_bucket'], 1)
    #    touch_file(sample, job, sample + '.vcf.done', f)
    #    
    #    file_dict['mergevs'] = True
    #    
    #if not file_dict['vcfstats'] and qstat_stdout.find('vcfstats') == -1:
    #    f.write(qstat_stdout + '\n')
    #    f.write('found %s.vcf.eval\n' % sample)
    #    get_stats_file(sample, sample + '.vcf.eval', f)
    #    job, bucket_file = put_file_in_s3(sample, sample + '.vcf.eval', parameters['s3_bucket'], 1)
    #    get_stats_file(sample, sample + '.vcf.snpden', f)
    #    job, bucket_file = put_file_in_s3(sample, sample + '.vcf.snpden', parameters['s3_bucket'], 1)
    #    touch_file(sample, job, sample + '.vcf.eval.done', f)
    #    
    #    file_dict['vcfstats'] = True
  
  f.write('Found all files\n')
  commands.getstatusoutput('sudo touch /var/www/%s.done' % sample)
  time.sleep(120)
  exit_status, term_stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq_%s' % sample)
  f.write(term_stdout + '\n')
  
  time.sleep(300)
  exit_status, term_stdout = commands.getstatusoutput('sudo starcluster removekey -c stormseq_starcluster_%s' % sample)
  f.write(term_stdout + '\n')
  
  exit_status, term_stdout = commands.getstatusoutput('sudo starcluster lv -n stormseq_%s | grep volume_id' % sample)
  vol = term_stdout.strip().split(': ')[1]
  f.write("Volume was: %s" % vol)
  f.write(term_stdout + '\n')
  
  exit_status, term_stdout = commands.getstatusoutput('sudo starcluster rv %s' % vol)
  f.close()

except Exception, e:
  f.write('Error: %s\n' % e)
  sys.exit()
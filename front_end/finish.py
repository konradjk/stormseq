import time, json, sys, copy
import commands, subprocess
from helpers import *

f = open("/tmp/final_log.txt","w")
parameters = json.loads(sys.argv[1])
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()
check_command = "sudo starcluster sshmaster stormseq 'qstat'"
es, stdout = commands.getstatusoutput(check_command)

# Check for jobs being done
files_to_get = ['mergef', 'depth', 'mergev', 'vcfstat']
file_dict = dict(zip(files_to_get, len(files_to_get)*[False]))
while True:
    if sum(file_dict.values()) == 4:
        break
    
    es, stdout = commands.getstatusoutput(check_command)
    
    if not file_dict['mergef'] and stdout.find('mergef') == -1:
        job, bucket_file = put_file_in_s3(parameters, 'final.bam', 1, f)
        touch_file(job, bucket_file, f)
        
        get_stats_file(parameters, 'final.stats.tar.gz', f)
        job, bucket_file = put_file_in_s3(parameters, 'final.stats.tar.gz', 1, f)
        touch_file(job, bucket_file, f)
        
        file_dict['mergef'] = True
      
    if not file_dict['depth'] and stdout.find('depth') == -1:
        get_stats_file(parameters, 'depth.stats.tar.gz', f)
        job, bucket_file = put_file_in_s3(parameters, 'depth.stats.tar.gz', 1, f)
        touch_file(job, bucket_file, f)
        
        file_dict['depth'] = True
        
    if not file_dict['mergev'] and stdout.find('mergev') == -1:
        job, bucket_file = put_file_in_s3(parameters, 'vcf', 1, f)
        touch_file(job, bucket_file, f)
        
        file_dict['mergev'] = True
        
    if not file_dict['vcfstat'] and stdout.find('vcfstat') == -1:
        get_stats_file(parameters, 'vcf.eval', f)
        job, bucket_file = put_file_in_s3(parameters, 'vcf.eval', 1, f)
        touch_file(job, bucket_file, f)
        
        file_dict['vcfstat'] = True
        
    time.sleep(10)

#exit_status, stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq')
#f.write(stdout + '\n')
#
#exit_status, stdout = commands.getstatusoutput('sudo starcluster removekey stormseq_starcluster_%s' % parameters['instance'])
#f.write(stdout + '\n')

# TODO: Get volume IDs from all volumes with snapshot corresponding to stormseq AMI, and delete

f.close()
#!/usr/bin/env python
import cgi
import os, glob, sys, time
import json
import commands, subprocess
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *

def cluster_fail(fail_string):
    print 'Content-Type: text/html'
    print
    print 'cluster-fail'
    sys.stdout.write(fail_string)
    sys.exit()

def get_job_id(input_string):
    lines = input_string.strip().split('\n')
    for line in lines:
        if line.find('has been submitted') > -1:
            return line.split()[2]
    return None

redirect_url = "/"
form = cgi.FieldStorage()
parameters = json.loads(form.getvalue('all_objects'))

ref_paths = { 'hg19' : '/data/hg19/hg19.fa',
              'ceu_ref' : '/data/ceu_ref/ceu_ref.fa',
              'hg18' : '/data/hg18/hg18.fa' }
dbsnp_paths = { 'dbsnp135' : '/data/dbsnp/dbsnp_135.vcf',
                'dbsnp132' : '/data/dbsnp/dbsnp_132.vcf' }

f = open("/tmp/mapping_log.txt","w")
files, ext = get_files('/mnt/stormseq_data', f)
check_certs_and_setup_env(f)
exit_status, volume_info = commands.getstatusoutput('ec2-describe-volumes -F tag:Name=stormseq_data | grep ^VOLUME')
volume_id = volume_info.split()[1]
f.write(volume_info + '\n')

if volume_id.find('vol-') != 0:
    print 'Content-Type: text/html'
    print
    sys.stdout.write('cert-fail')
    sys.exit()

# Should check if anything is using the disk, otherwise this hangs
if volume_info.find('available') == -1:
  exit_status, stdout = commands.getstatusoutput('sudo umount /dev/xvdf')
  f.write(stdout + '\n')
  exit_status, stdout = commands.getstatusoutput('ec2-detach-volume %s' % volume_id)
  f.write(stdout + '\n')
  while stdout.find('available') == -1:
    exit_status, stdout = commands.getstatusoutput('ec2-describe-volumes -F tag:Name=stormseq_data | grep ^VOLUME')
    
fq_files = [fq_file.replace('/mnt/stormseq_data', '/mydata') for fq_file in files]

parameters = write_config_file(parameters, len(files)/2, f, volume_id=volume_id)
f.flush()
exit_status, stdout = commands.getstatusoutput('sudo starcluster createkey -o /root/.ssh/stormseq_starcluster.rsa stormseq_starcluster_%s' % parameters['instance'])
f.write(stdout + '\n')
exit_status, stdout = commands.getstatusoutput('sudo starcluster start stormseq')
f.write(stdout + '\n')
if stdout.find('The cluster is now ready to use.') == -1:
    cluster_fail('Something went wrong starting the cluster')
#exit_status, stdout = commands.getstatusoutput('sudo starcluster put stormseq /root/*py /root/')
#f.write(stdout + '\n')
    
ref = ref_paths[parameters['genome_version']]
add_ext = '.fq.gz' if ext == '.gz' else '.fq'
all_mapping_jobs = []
all_sorted_bams = []
for fq1 in fq_files:
    if fq1.find('_1' + add_ext) == -1:
        continue
    fq2 = fq1.replace('_1' + add_ext, '_2' + add_ext)
    if parameters['alignment_pipeline'] == 'bwa':
        try:
            quality = int(parameters['bwa-opt-q'])
        except ValueError:
            quality = 20
        sample = parameters['sample_name']
        map_command = "sudo starcluster sshmaster stormseq 'qsub -b y -cwd python bwa-map.py --fq1=%s --fq2=%s --reference=%s --quality=%s --sample=%s'" % (fq1, fq2, ref, quality, sample)
    elif parameters['alignment_pipeline'] == 'snap':
        map_command = 'qsub -b y -cwd echo'
    f.write(map_command + '\n')
    exit_status, stdout = commands.getstatusoutput(map_command)
    f.write(stdout + '\n')  
    job = get_job_id(stdout)      
    if job is None:
        cluster_fail('Something went wrong starting your jobs.')     
    all_mapping_jobs.append(job)       
    all_sorted_bams.append(fq1.replace('_1' + add_ext, '.sorted.bam'))

merge_command = "sudo starcluster sshmaster stormseq 'qsub -hold_jid %s -b y -cwd python merge.py --bams=%s --output=/mydata/%s'" % (','.join(all_mapping_jobs), ','.join(all_sorted_bams), parameters['sample_name'] + '.merged.bam')
exit_status, stdout = commands.getstatusoutput(merge_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

def put_file_in_s3(parameters, type, hold, log):
  upload_command = "sudo starcluster sshmaster stormseq".split(' ')
  current_date = time.strftime("%d%m%Y", time.gmtime())
  local_file = '/mydata/%s.%s' % (parameters['sample_name'], type)
  bucket_file = '%s_stormseq_%s.%s' % (parameters['sample_name'], current_date, type)
  cmd_opts = (hold, parameters['access_key_id'], parameters['secret_access_key'], local_file, parameters['s3_bucket'], bucket_file)
  args = "'qsub -hold_jid %s -cwd -b y python /root/s3afe.py --aws_access_key_id=%s --aws_secret_access_key=%s --filename=%s --bucketname=%s --keyname=%s'" % cmd_opts
  upload_command.append(args)
  stdout = subprocess.check_output(upload_command)
  job = get_job_id(stdout)
  log.write('%s\n' % str(stdout))
  return (job, bucket_file)

job, bucket_file = put_file_in_s3(parameters, 'merged.bam', job, f)
command = "sudo starcluster sshmaster stormseq 'qsub -hold_jid %s -cwd -b y touch /mydata/%s'" % (job, bucket_file)
exit_status, stdout = commands.getstatusoutput(command)
f.write('%s\n' % str(stdout))

job, bucket_file = put_file_in_s3(parameters, 'merged.stats.tar.gz', job, f)

f.write(json.dumps(parameters) + '\n')
p = subprocess.Popen(['python', '/root/run_cleaning.py', json.dumps(parameters)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
f.write('%s\n' % p.pid)
f.close()

print 'Content-Type: text/html'
print
sys.stdout.write('success')
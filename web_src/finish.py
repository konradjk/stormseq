import time, json, sys, copy
import commands, subprocess

ref_paths = { 'hg19' : '/data/hg19/hg19.fa',
              'ceu_ref' : '/data/ceu_ref/ceu_ref.fa',
              'hg18' : '/data/hg18/hg18.fa' }
dbsnp_paths = { 'dbsnp135' : '/data/dbsnp/dbsnp_135.vcf',
                'dbsnp132' : '/data/dbsnp/dbsnp_132.vcf' }

def get_job_id(input_string):
    lines = input_string.strip().split('\n')
    for line in lines:
        if line.find('has been submitted') > -1:
            return line.split()[2]
    return None

starcluster = "sudo starcluster sshmaster stormseq".split(' ')

f = open("/tmp/final_log.txt","w")
parameters = json.loads(sys.argv[1])
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()
check_command = "sudo starcluster sshmaster stormseq 'qstat'"
es, stdout = commands.getstatusoutput(check_command)
while len(stdout.split('\n')) > 5:
    es, stdout = commands.getstatusoutput(check_command)
    time.sleep(10)

def put_file_in_s3(parameters, type, hold, log):
  upload_command = "sudo starcluster sshmaster stormseq".split(' ')
  current_date = time.strftime("%d%m%Y", time.gmtime())
  local_file = '/mydata/%s.%s' % (parameters['sample_name'], type)
  bucket_file = '%s_stormseq_%s.%s' % (parameters['sample_name'], current_date, type)
  cmd_opts = (hold, parameters['access_key_id'], parameters['secret_access_key'], local_file, parameters['s3_bucket'], bucket_file)
  args = "'qsub -hold_jid %s -cwd -b y python /root/s3afe.py --aws_access_key_id=%s --aws_secret_access_key=%s --filename=%s --bucketname=%s --keyname=%s'" % cmd_opts
  upload_command.append(args)
  stdout = subprocess.check_output(upload_command, stderr=subprocess.PIPE)
  job = get_job_id(stdout)
  log.write('Getting from: %s\n' % str(stdout))
  return (job, bucket_file)

def get_stats_file(parameters, ext, log):
    get_command = "sudo starcluster get stormseq".split(' ')
    stats_filename = "%s.%s" % (parameters['sample_name'], ext)
    get_command.append("/mydata/%s" % stats_filename)
    get_command.append("/var/www/%s" % stats_filename)
    stdout = subprocess.check_output(get_command)
    log.write(stdout + '\n')
    if stats_filename.endswith('.tar.gz'):
      command = "tar zxv -C /var/www/ -f /var/www/%s" % stats_filename
      log.write(command + '\n')
      stdout = subprocess.check_output(command.split())
      log.write(stdout + '\n')

get_stats_file(parameters, 'final.stats.tar.gz', f)

# Make cluster smaller for post-processing
nodes_to_remove = ' '.join(['node%03d' % x for x in range(2, 25)])
nodes_command = "sudo starcluster rn %s stormseq" % nodes_to_remove
try:
  exit_status = subprocess.call(nodes_command.split(' '), stdout=f)
except subprocess.CalledProcessError:
  pass

# Put stats, VCF, and final BAM files in bucket
job, bucket_file = put_file_in_s3(parameters, 'final.stats.tar.gz', 1, f)

job, bucket_file = put_file_in_s3(parameters, 'vcf', 1, f)

upload_command = copy.deepcopy(starcluster)
args = "'qsub -cwd -b y -hold_jid %s touch /mydata/%s'" % (job, bucket_file)
upload_command.append(args)
f.write(' '.join(upload_command))
stdout = subprocess.check_output(upload_command)
f.write('%s\n' % str(stdout))

job, bucket_file = put_file_in_s3(parameters, 'final.bam', 1, f)

upload_command = copy.deepcopy(starcluster)
args = "'qsub -cwd -b y -hold_jid %s touch /mydata/%s'" % (job, bucket_file)
upload_command.append(args)
stdout = subprocess.check_output(upload_command)
f.write('%s\n' % str(stdout))

vcf_stats_command = "sudo starcluster sshmaster stormseq 'qsub -b y -cwd python vcf-stats.py --reference=%s --dbsnp=%s --input=/mydata/%s.vcf --output=/mydata/%s.vcf.eval'" % (ref_paths[parameters['genome_version']], dbsnp_paths[parameters['dbsnp_version']], parameters['sample_name'], parameters['sample_name'])
exit_status, stdout = commands.getstatusoutput(vcf_stats_command)
f.write(stdout + '\n')
job = get_job_id(stdout)

job, bucket_file = put_file_in_s3(parameters, 'vcf.eval', job, f)

depth_command = "sudo starcluster sshmaster stormseq 'qsub -b y -cwd python depth.py --reference=%s --input=/mydata/%s.final.bam --output=/mydata/%s.depth'" % (ref_paths[parameters['genome_version']], parameters['sample_name'], parameters['sample_name'])
f.write(depth_command)
exit_status, stdout = commands.getstatusoutput(depth_command)
f.write(stdout + '\n')
job = get_job_id(stdout)

job, bucket_file = put_file_in_s3(parameters, 'depth.stats.tar.gz', job, f)
f.flush()
time.sleep(300)
es, stdout = commands.getstatusoutput(check_command)
while len(stdout.split('\n')) > 5:
    es, stdout = commands.getstatusoutput(check_command)
    time.sleep(10)

get_stats_file(parameters, 'final.eval', f)

get_stats_file(parameters, 'merged.stats.tar.gz', f)

#exit_status, stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq')
#f.write(stdout + '\n')
#
#exit_status, stdout = commands.getstatusoutput('sudo starcluster removekey stormseq_starcluster_%s' % parameters['instance'])
#f.write(stdout + '\n')

# TODO: Get volume IDs from all volumes with snapshot corresponding to stormseq AMI, and delete

f.close()
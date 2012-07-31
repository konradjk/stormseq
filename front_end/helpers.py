import os, glob, commands, sys

ref_paths = {
  'hg19' : '/data/hg19/hg19.fa',
  'ceu_ref' : '/data/ceu_ref/ceu_ref.fa',
  'hg18' : '/data/hg18/hg18.fa' }
dbsnp_paths = {
  'dbsnp135' : '/data/dbsnp/dbsnp_135.vcf',
  'dbsnp132' : '/data/dbsnp/dbsnp_132.vcf' }
amis = {'hg19': 'ami-515bf338'}
instances = {'bwa' : 'm1.large',
  'snap' : 'm2.4xlarge'}

starcluster = "sudo starcluster sshmaster stormseq".split(' ')

# Failure types
def cluster_fail(fail_string):
    print 'Content-Type: text/html'
    print
    print 'cluster-fail'
    sys.stdout.write(fail_string)
    sys.exit()

def qc_fail(fail_string):
    print 'Content-Type: text/html'
    print
    print 'qc-fail'
    sys.stdout.write(fail_string)
    sys.exit()

def check_certs_and_setup_env(log):
    pk = glob.glob('/root/pk-*pem')
    cert = glob.glob('/root/cert-*pem')
    log.write('pk is: %s\n' % pk)
    log.write('cert is: %s\n' % cert)
    if len(pk) > 0 and len(cert) > 0:
        os.environ['EC2_PRIVATE_KEY'] = pk[0]
        os.environ['EC2_CERT'] = cert[0]
    else:
        print 'Content-Type: text/html'
        print
        sys.stdout.write('cert-fail')
        sys.exit()

def get_job_id(input_string):
    lines = input_string.strip().split('\n')
    for line in lines:
        if line.find('has been submitted') > -1:
            return line.split()[2]
    return None

def get_files(this_dir, log):
    all_files = [os.path.join(this_dir, file) for file in os.listdir(this_dir)]
    files = [file for file in all_files if file.endswith('.fq.gz') or file.endswith('.fastq.gz')]
    if len(files) == 0:
        files = [file for file in all_files if file.endswith('.fq')]
    if len(files) == 0:
        files = [file for file in all_files if file.endswith('.fastq')]
    if len(files) == 0:
      qc_fail('No files found')
    if len(files) % 2:
      qc_fail('Odd number of *' + os.path.splitext(files[0])[1] + ' files found')
    ext = os.path.splitext(files[0])[1]
    return (files, ext)

def write_config_file(parameters, number_of_processes, log, volume_id=None):
    exit_status, instance = commands.getstatusoutput('ec2-describe-instances --filter tag:Name=stormseq --filter instance-state-name=running | grep ^INSTANCE | cut -f2')
    parameters['number_of_processes'] = number_of_processes
    parameters['ami'] = amis[parameters['genome_version']]
    parameters['instance_type'] = instances[parameters['alignment_pipeline']]
    if volume_id is None:
        exit_status, volume_info = commands.getstatusoutput('ec2-describe-volumes -F tag:Name=stormseq_data | grep ^VOLUME')
        volume_id = volume_info.split()[1]
        log.write(volume_info + '\n')
    parameters['volume_id'] = volume_id
    if parameters['alignment_pipeline'] == 'snap':
      try:
        parameters['spot_request'] = '' if parameters['request_type'] != 'spot' else 'SPOT_BID = %s' % float(parameters['hi-mem-bid'])
      except ValueError:
        parameters['spot_request'] = ''
    else:
      try:
        parameters['spot_request'] = '' if parameters['request_type'] != 'spot' else 'SPOT_BID = %s' % float(parameters['large-bid'])
      except ValueError:
        parameters['spot_request'] = ''
    parameters['instance'] = instance
    
    output_config = open('/root/.starcluster/config', 'w')
    log.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
    in_string = open('/root/default_starcluster_config.txt').read()
    output_config.write(in_string % parameters)
    output_config.close()
    return parameters

# Later on
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
    try:
        stdout = subprocess.check_output(get_command, stderr=f)
    except subprocess.CalledProcessError, e:
        f.write(str(e) + '\n')
    log.write(stdout + '\n')
    if stats_filename.endswith('.tar.gz'):
        command = "tar zxv -C /var/www/ -f /var/www/%s" % stats_filename
        log.write(command + '\n')
        stdout = subprocess.check_output(command.split())
        log.write(stdout + '\n')

def touch_file(job, bucket_file, log):
    upload_command = copy.deepcopy(starcluster)
    args = "'qsub -cwd -b y -hold_jid %s touch /mydata/%s'" % (job, bucket_file)
    upload_command.append(args)
    log.write(' '.join(upload_command))
    stdout = subprocess.check_output(upload_command)
    log.write('%s\n' % str(stdout))
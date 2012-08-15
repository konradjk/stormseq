import os, glob, sys
import subprocess, commands
import time
import copy
import shutil
import re
from collections import defaultdict

ref_paths = {
  'hg19' : '/data/hg19/hg19.fa',
  'ceu_ref' : '/data/ceu_ref/ceu_ref.fa' }
dbsnp_paths = {
  'dbsnp135' : '/data/dbsnp/dbsnp_135.vcf',
  'dbsnp132' : '/data/dbsnp/dbsnp_132.vcf' }
amis = {
  'hg19': 'ami-6daa1f04',
  'hg19-himem' : 'ami-XXXXXXX'}
instances = {
  'bwa' : 'm1.large',
  'snap' : 'm2.4xlarge'}

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
    
def file_error(fail_string):
    print 'Content-Type: text/html'
    print
    print 'file-fail'
    sys.stdout.write(fail_string)
    sys.exit()

def generic_response(output):
    print 'Content-Type: text/html'
    print
    sys.stdout.write(output)
    sys.exit()

def get_chroms():
  chroms = ['chr%s' % x for x in range(1,23)]
  chroms.extend(['chrX', 'chrY', 'chrM'])
  return chroms

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

def setup_s3cfg(parameters, outfile=None):
    outfile = outfile if outfile is not None else '/root/.s3cfg'
    shutil.copyfile('/root/.s3cfg_orig', outfile)
    output_config = open(outfile, 'a')
    output_config.write('''
access_key = %(access_key_id)s
secret_key = %(secret_access_key)s
''' % (parameters))
    output_config.close()

def check_files(parameters, dir, log):
    directory = 's3://%s/' % (parameters['s3_bucket'])
    directory += '' if dir is None else '%s/' % dir
    command = 'sudo s3cmd ls %s' % directory
    log.write(command + '\n')
    try:
        file_info = subprocess.check_output(command.split()).strip().split('\n')
    except subprocess.CalledProcessError, e:
        return None, None, None
    #log.write('\n'.join(file_info))
    allowed_exts = ['.bam', '.fq', '.fastq', '.gz']
    if len(file_info) == 0:
        return None, None, None
    files = [line.strip().split()[3] for line in file_info if not line.endswith('/')]
    total_size = sum([int(line.strip().split()[2]) for line in file_info if not line.endswith('/')])
    ext = os.path.splitext(files[0])[1]
    if ext not in allowed_exts:
        return None, None, None
    command = 'sudo s3cmd get %s -'
    command += ' | zcat | head -4' if ext == '.gz' else ' | head -4'
    output_files = defaultdict(dict)
    for file in files:
        if ext == '.bam':
            read = file
            output_files[read]['1'] = file
            output_files[read]['2'] = file
        else:
            this_command = command % file
            #log.write(this_command + '\n')
            head_lines = commands.getoutput(this_command).split('\n')
            first_line = head_lines[0].strip().split('/')
            #log.write(head_lines[0] + '\n')
            if len(first_line) != 2:
                qc_fail('Malformed paired end file (read name should have /1 or /2 tag)')
            read, pair = first_line
            output_files[read][pair] = file
    return (output_files, ext, total_size)


def write_basic_config_file(parameters, sample):
    parameters['sample'] = sample
    output_config = open('/root/.starcluster/config', 'w')
    in_string = open('/root/basic_starcluster_config.txt').read()
    output_config.write(in_string % parameters)
    output_config.close()

def replace_zone_in_config_file(zone, sample):
    with open('/root/.starcluster/config', 'r') as cnf:
        config = cnf.readlines()
    for i, line in enumerate(reversed(config)):
        if line.find('AVAILABILITY_ZONE') > -1:
            config[len(config) - i - 1] = 'AVAILABILITY_ZONE = %s\n' % zone
            break
    with open('/root/.starcluster/config', 'w') as cnf:
      cnf.write(''.join(config))

def add_to_config_file(parameters, sample):
    parameters['sample'] = sample
    parameters['ami'] = amis[parameters['genome_version']]
    parameters['instance_type'] = parameters['force_large_machine'] if parameters['force_large_machine'] != 'default' else instances[parameters['alignment_pipeline']]
    bid = parameters['hi-mem-bid'] if parameters['instance_type'] == 'm2.4xlarge' else parameters['large-bid']
    try:
      parameters['spot_request'] = '' if parameters['request_type'] != 'spot' else 'SPOT_BID = %s' % float(bid)
    except ValueError:
      parameters['spot_request'] = ''
    
    output_config = open('/root/.starcluster/config', 'a')
    in_string = open('/root/add_starcluster_config.txt').read()
    output_config.write(in_string % parameters)
    output_config.close()
    
def add_volume_to_config_file(volume, sample):
    output_config = open('/root/.starcluster/config', 'a')
    in_string = open('/root/volume_starcluster_config.txt').read()
    output_config.write(in_string % { 'volume': volume, 'sample': sample })
    output_config.close()

# Later on
def put_file_in_s3(sample, fname, bucket, hold):
    upload_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
    current_date = time.strftime("%Y%m%d", time.gmtime())
    bucket_file = re.sub(sample, sample + '_stormseq_%s' % current_date, fname)
    args = "'qsub -hold_jid %s -q all.q@master,all.q@node001 -cwd -b y s3cmd -c /mydata/.s3cfg put /mydata/%s s3://%s/%s'" % (hold, fname, bucket, bucket_file)
    upload_command.append(args)
    stdout = subprocess.check_output(upload_command, stderr=subprocess.PIPE)
    job = get_job_id(stdout)

    upload_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
    args = "'qsub -hold_jid %s -cwd -b y touch /mydata/%s'" % (job, fname)
    upload_command.append(args)
    stdout = subprocess.check_output(upload_command, stderr=subprocess.PIPE)
    job = get_job_id(stdout)
    return (job, bucket_file)

def get_stats_file(sample, fname, log):
    get_command = ("sudo starcluster get stormseq_%s" % sample).split(' ')
    get_command.append("/mydata/%s" % fname)
    get_command.append("/var/www/%s" % fname)
    log.write('getting: %s\n' % ' '.join(get_command))
    try:
        stdout = subprocess.check_output(get_command, stderr=log)
    except subprocess.CalledProcessError, e:
        log.write(str(e) + '\n')
        log.flush()
        sys.exit()
    log.write(stdout + '\n')
    log.flush()
    if fname.endswith('.tar.gz'):
        command = "tar zxv -C /var/www/ -f /var/www/%s" % fname
        log.write(command + '\n')
        stdout = subprocess.check_output(command.split())
        log.write(stdout + '\n')

def touch_file(sample, hold, file, log):
    upload_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
    args = "'qsub -cwd -b y -hold_jid %s touch /mydata/%s'" % (hold, file)
    upload_command.append(args)
    log.write(' '.join(upload_command))
    stdout = subprocess.check_output(upload_command)
    log.write('%s\n' % str(stdout))
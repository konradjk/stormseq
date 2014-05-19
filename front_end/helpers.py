import os, glob, sys
import subprocess, commands
import time
import copy
import shutil
import re
from collections import defaultdict
import boto

ref_paths = {
    'hg19' : '/data/hg19/hg19.fa',
    'ceu_ref' : '/data/ceu_ref/ceu_ref.fa' }
dbsnp_paths = {
    'dbsnp137' : '/data/dbsnp/dbsnp_137.vcf',
    'dbsnp135' : '/data/dbsnp/dbsnp_135.vcf',
    'dbsnp132' : '/data/dbsnp/dbsnp_132.vcf' }
amis = {
    'hg19': 'ami-fbece192',
    'hg19-himem' : 'ami-XXXXXXX'}
instances = {
    'bwa' : 'm1.large',
    'bwa-mem' : 'c1.xlarge',
    'snap' : 'm2.4xlarge'}
# Allowed instances encodes which instances can be run for each algorithm, and how many files can be run per node
allowed_instances = {
    'bwa' : {
        'm1.large' : 1,
        'm1.xlarge' : 2,
        'c1.xlarge' : 1,
        'm2.4xlarge' : 4
    },
    'bwa-mem' : {
        'm1.large' : 1,
        'm1.xlarge' : 2,
        'c1.xlarge' : 1,
        'm2.4xlarge' : 4
    },
    'snap' : { 'm2.4xlarge' : 1 }
}

root = '/usr/local/bin/'
bwa_binary = '%s/bwa-0.7.5a/bwa' % root
samtools_binary = '%s/samtools' % root
samtools_mt_binary = '%s/samtools-multi/samtools' % root
snap_binary = '%s/snap' % root

picard_rg_binary = '%s/picard/AddOrReplaceReadGroups.jar' % root
picard_convert_binary = '%s/picard/SamToFastq.jar' % root
picard_merge_binary = '%s/picard/MergeSamFiles.jar' % root
picard_stats_binary = '%s/picard/CollectMultipleMetrics.jar' % root
picard_binary = '%s/picard/MarkDuplicates.jar' % root

gatk_lite_binary = '%s/GenomeAnalysisTKLite-2.1-12-g2d7797a/GenomeAnalysisTKLite.jar' % root
gatk_binary = gatk_lite_binary
#gatk_binary = '%s/GenomeAnalysisTK-2.7-4-g6f46d11/GenomeAnalysisTK.jar' % root
bcftools_binary = '%s/bcftools' % root
vcfutils_binary = '%s/vcfutils.pl' % root

vcftools_binary = '%s/vcftools' % root
vep_binary = '%s/variant_effect_predictor/variant_effect_predictor.pl' % root

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

    output_config = open('/root/.boto', 'w')
    output_config.write('''[Credentials]
aws_access_key_id = %(access_key_id)s
aws_secret_access_key = %(secret_access_key)s
''' % (parameters))
    output_config.close()

def check_files(parameters, dir, log):
    directory = 's3://%s/' % (parameters['input_s3_bucket'])
    directory += '' if dir is None else '%s/' % dir
    command = 'sudo s3cmd ls %s' % directory
    log.write(command + '\n')
    try:
        file_text = subprocess.check_output(command.split())
        file_info = file_text.strip().split('\n')
    except subprocess.CalledProcessError, e:
        return None, None, None
        #log.write('\n'.join(file_info))
    allowed_exts = ['.bam', '.fq', '.fastq']
    if len(file_info) == 0 or file_text == '':
        return None, None, None
    files = [line.strip().split()[3] for line in file_info if not line.endswith('/')]
    sizes = [int(line.strip().split()[2]) for line in file_info if not line.endswith('/')]
    total_size = 0
    output_files = defaultdict(dict)
    for i, file in enumerate(files):
        ext = os.path.splitext(file)[1]
        gzipped = ext == '.gz'
        command = 'sudo s3cmd-noretry get %s - '
        if gzipped:
            ext = os.path.splitext(os.path.splitext(file)[0])[1]
            command += '| zcat | head -4'
        else:
            command += '| head -4'
        if ext == '.bam':
            read = file
            output_files[read]['1'] = file
            output_files[read]['2'] = file
            total_size += sizes[i]*8
        elif ext in allowed_exts:
            this_command = command % file
            #log.write(this_command + '\n')
            head_lines = commands.getoutput(this_command).split('\n')
            first_line = head_lines[0].strip().split('/')
            #log.write(head_lines[0] + '\n')
            read = None
            pair = None
            if len(first_line) == 2:
                # Original format
                read, pair = first_line
            else:
                # Support for CASAVA 1.8+
                first_line = head_lines[0].strip().split()
                if len(first_line) == 2 and ':' in first_line[1]:
                    read = first_line[0]
                    pair = first_line[1].split(':')[0]
            if read is None or pair is None:
                qc_fail('Malformed paired end file (read name should have /1 or /2 tag; or 1:N:0... format)')
            output_files[read][pair] = file
            total_size += sizes[i]*8 if gzipped else sizes[i]*4
    total_size = int(total_size/1E9) + 100
    if len(output_files) == 0:
        return None, None, None
    else:
        return (output_files, ext, total_size)

def s3_signed_url(parameters, file_path):
    s3conn = boto.connect_s3(parameters['access_key_id'], parameters['secret_access_key'])
    bucket = s3conn.get_bucket(parameters['input_s3_bucket'], validate=False)
    key = bucket.new_key(file_path)
    signed_url = key.generate_url(expires_in=86400)
    return signed_url

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
    try:
        parameters['spot_request'] = '' if parameters['request_type'] != 'spot' else 'SPOT_BID = %s' % float(parameters['spot_bid'])
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

def remove_volume_from_config_file(sample):
    config = []
    skip = False
    with open('/root/.starcluster/config', 'r') as cnf:
        for line in cnf:
            if line.find('[') > -1:
                skip = False
            if line.find('[volume stormseq_%s]' % sample) > -1:
                skip = True
            if not skip and line.find('volumes = stormseq_%s' % sample) == -1:
                config.append(line)
    with open('/root/.starcluster/config', 'w') as cnf:
        cnf.write(''.join(config))

# Later on
def put_file_in_s3(sample, ext, bucket, hold, cluster=False):
    current_date = time.strftime("%Y%m%d", time.gmtime())
    bucket_file = '%s_stormseq_%s.%s' % (sample, current_date, ext)
    #args = "'qsub -hold_jid %s -q all.q@master,all.q@node001 -cwd -b y s3cmd -v -c /mydata/.s3cfg put /mydata/%s s3://%s/%s'" % (hold, fname, bucket, bucket_file)

    upload_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
    args = "qsub -hold_jid %s -q all.q@master,all.q@node001 -cwd -b y s3-mp-upload.py -n 8 /mydata/%s.%s s3://%s/%s" % (hold, sample, ext, bucket, bucket_file)
    if cluster:
        upload_command = args.split()
    else:
        upload_command.append("'" + args + "'")

    stdout = subprocess.check_output(upload_command, stderr=subprocess.PIPE)
    job = get_job_id(stdout)

    upload_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
    args = "qsub -hold_jid %s -cwd -b y touch /mydata/%s.%s.done" % (job, sample, ext)
    if cluster:
        upload_command = args.split()
    else:
        upload_command.append("'" + args + "'")
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

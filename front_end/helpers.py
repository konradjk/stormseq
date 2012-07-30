import os, glob, commands, sys

def get_files(this_dir, log):
    files = glob.glob(this_dir + '/*.gz')
    if len(files) == 0:
      files = glob.glob(this_dir + '/*.fq')
    if len(files) == 0:
      files = glob.glob(this_dir + '/*.fastq')
    log.write(','.join(files) + '\n')
    if len(files) == 0:
        qc_fail('No files found')
    if len(files) % 2:
        qc_fail('Odd number of *' + os.path.splitext(files[0])[1] + ' files found')
    ext = os.path.splitext(files[0])[1]
    return (files, ext)

def write_config_file(parameters, number_of_processes, log, volume_id=None):
    amis = {'hg19': 'ami-8779d1ee'}
    instances = {'bwa' : 'm1.large',
                 'snap' : 'm2.4xlarge'}
    
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
      parameters['spot_request'] = '' if parameters['request_type'] != 'spot' else 'SPOT_BID = %s' % parameters['hi-mem-bid']
    else:
      parameters['spot_request'] = '' if parameters['request_type'] != 'spot' else 'SPOT_BID = %s' % parameters['large-bid']
    parameters['instance'] = instance
    
    output_config = open('/root/.starcluster/config', 'w')
    log.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
    in_string = open('/root/default_starcluster_config.txt').read()
    output_config.write(in_string % parameters)
    output_config.close()
    return parameters

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
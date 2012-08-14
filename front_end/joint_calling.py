#!/usr/bin/env python
import cgi
import os, glob, sys, time, re
import json
import commands, subprocess
from collections import defaultdict
import cgitb; cgitb.enable()  # for troubleshooting
from helpers import *
import string

parameters = json.loads(sys.argv[1])

f = open("/tmp/joint_calling_log.txt","w")
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()

while True:
  samples_done = 0
  for sample_name in parameters['sample_names']:
    samples_done += os.path.exists('/var/www/%s.done' % sample_name)
  if samples_done == len(parameters['sample_names']):
    break
  time.sleep(120)

sample = 'call_all_samples'
zones = ['us-east-1%s' % letter for letter in 'bde']
zone = zones[0]
parameters['zone'] = zone
parameters['number_of_processes'] = 4
parameters['force_large_machine'] = 'm2.4xlarge'
add_to_config_file(parameters, sample)

try:
  command = 'sudo starcluster terminate -c stormseq_%s' % sample
  stdout = subprocess.check_output(command.split())
except Exception, e:
  pass

try:
  check_volume_command = "sudo starcluster lv --name=stormseq_%s" % sample
  stdout = subprocess.check_output(check_volume_command.split())
  volume_id = [line.split()[1] for line in stdout.split('\n') if line.find('volume_id') > -1][0]
  check_volume_command = "sudo starcluster rv -c %s" % volume_id
  stdout = subprocess.check_output(check_volume_command.split())
except Exception, e:
  pass

try:
  command = 'sudo starcluster rk -c stormseq_starcluster_%s' % (sample)
  stdout = subprocess.check_output(command.split())
except Exception, e:
  pass

try:
  command = 'rm /root/.ssh/stormseq_starcluster_%s.rsa' % (sample)
  stdout = subprocess.check_output(command.split())
except Exception, e:
  pass

command = 'sudo starcluster createkey -o /root/.ssh/stormseq_starcluster_%s.rsa stormseq_starcluster_%s' % (sample, sample)
stdout = subprocess.check_output(command.split())
f.write(stdout + '\n')

size = len(parameters['sample_names'])
while True:
  try:
    create_volume_command = "sudo starcluster createvolume --shutdown-volume-host --name=stormseq_%s %s %s" % (sample, size, zone)
    stdout = subprocess.check_output(create_volume_command.split(), stderr=subprocess.STDOUT)
    break
  except subprocess.CalledProcessError, e:
    f.write(str(e.output) + '\n')
    if e.output.find('The requested Availability Zone is currently constrained') > -1:
      zones.pop(index % len(zones))
      zone = zones[index % len(zones)]
      replace_zone_in_config_file(zone, sample)
    else:
      generic_response('Failed to create volume. Error: %s' % e.output)

check_volume_command = "sudo starcluster lv --name=stormseq_%s" % sample
stdout = subprocess.check_output(check_volume_command.split())
if stdout.find('volume_id') == -1:
  generic_response('Failed to create volume')
volume_id = [line.split()[1] for line in stdout.split('\n') if line.find('volume_id') > -1][0]
add_volume_to_config_file(volume_id, sample)
while stdout.find('available') == -1:
  time.sleep(5)
  stdout = subprocess.check_output(check_volume_command.split())

# Start cluster
start_command = 'sudo starcluster start --cluster-template=stormseq_%s stormseq_%s' % (sample, sample)
stdout = subprocess.check_output(start_command.split(), stderr=subprocess.STDOUT)
f.write(stdout + '\n')
f.flush()
if stdout.find('The cluster is now ready to use.') == -1:
  cluster_fail('Something went wrong starting the cluster')

config_file = 'stormseq_%s.cnf' % sample
with open(config_file, 'w') as cnf:
  cnf.write(json.dumps({ 'parameters' : parameters, 'sample' : sample }))
stdout = commands.getoutput('sudo starcluster put stormseq_%s %s /mydata/' % (sample, config_file))
f.write(stdout + '\n')
f.flush()

command = ('sudo starcluster sshmaster stormseq_%s' % sample).split()
command.append("'qsub -cwd -b y python call_all_samples.py --config_file=/mydata/%s'" % config_file)
f.write(' '.join(command) + '\n')
stdout = subprocess.check_output(command)

time.sleep(300)
check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
check_command.append("'qstat'")
stdout = subprocess.check_output(check_command)
f.write('%s\nlength: %s\n' % (stdout, len(stdout.split('\n'))))
while len(stdout.split('\n')) > 5:
    stdout = subprocess.check_output(check_command)
    time.sleep(10)

# Put files in S3 and download files
put_file_in_s3(sample, 'stormseq_all_samples.vcf', parameters['s3_bucket'], 1)

exit_status, stdout = commands.getstatusoutput('sudo starcluster terminate -c stormseq_%s' % sample)
f.write(stdout + '\n')

exit_status, stdout = commands.getstatusoutput('sudo starcluster removekey -c stormseq_starcluster_%s' % sample)
f.write(stdout + '\n')

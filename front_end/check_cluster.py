import time, json, sys, copy, glob
import commands, subprocess
from helpers import *

config_file = sys.argv[1]
with open(config_file) as cnf:
  input = json.loads(cnf.readline())

sample = input['sample']
parameters = input['parameters']
parameters['sample_name'] = sample

time.sleep(300)
while True:
  time.sleep(3600)
  check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
  check_command.append("'qstat -f'")
  lines = subprocess.check_output(check_command).split('\n')
  
  delete_node = ''
  jobs_to_restart = []
  started = False
  for line in lines:
    if line.startswith('queuename'):
      started = True
      continue
    if not started:
      continue
    if line.strip() == '' or line.startswith('###'):
      break
    
    if line.startswith('---'):
      if delete_node != '':
        # Take down node
        check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
        check_command.append("'qmod -d %s'" % delete_node)
        subprocess.check_output(check_command)
        
        # Restart job(s) on that node
        for job in jobs_to_restart:
          check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
          check_command.append("'qmod -rj %s'" % job)
          subprocess.check_output(check_command)
      delete_node = ''
      jobs_to_restart = []
      continue
    
    if delete_node != '':
      # Check for jobs under that node, qalter -r y
      job = line.strip().split()[0]
      check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
      check_command.append("'qalter -r y %s'" % job)
      subprocess.check_output(check_command)
      jobs_to_restart.append(job)
    
    if line.startswith('all.q'):
      # Check if node is alarm, unreachable
      fields = line.strip().split()
      if len(fields) > 5:
        if fields[5].find('au') > -1:
          delete_node = fields[0]  
  


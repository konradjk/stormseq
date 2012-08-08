import time, json, sys, copy, glob
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

f = open("/tmp/cleaning_log_%s.txt" % sample, "w")

f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()

time.sleep(300)
check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
check_command.append("'qstat'")
stdout = subprocess.check_output(check_command)
f.write('%s\nlength: %s\n' % (stdout, len(stdout.split('\n'))))
while len(stdout.split('\n')) > 5:
    stdout = subprocess.check_output(check_command)
    time.sleep(10)

get_stats_file(sample, sample + '.merged.stats.tar.gz', f)

f.write('finished!\n')

if parameters['instance_type'] == 'm1.large':
  nodes_needed = min(parameters['max_on_zone'], 24)
elif parameters['instance_type'] == 'm2.4xlarge':
  nodes_needed = min(parameters['max_on_zone'], 4)
total_nodes = int(parameters['number_of_processes'])
f.write('have:\t%s nodes\nneed:\t%s nodes\n' % (total_nodes, nodes_needed))
f.flush()

if True:
 if total_nodes < nodes_needed:
    nodes_to_add = nodes_needed - total_nodes
    nodes_names_to_add = ','.join(['node%03d' % x for x in range(total_nodes, nodes_needed)])
    nodes_command = "sudo starcluster an -n %s -a %s stormseq_%s" % (nodes_to_add, nodes_names_to_add, sample)
    f.write(nodes_command + '\n')
    started = False
    failed = 0
    while not started:
      try:
        output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
        started = True
        f.write(output + '\n')
        f.flush()
      except subprocess.CalledProcessError, e:
        f.write(str(e) + '\n')
        f.flush()
        time.sleep(300)
        nodes_command = "sudo starcluster an -x -n %s -a %s stormseq_%s" % (nodes_to_add, nodes_names_to_add, sample)
        failed += 1
        if failed == 3:
          f.write('Failed 3 times. Exiting...\n')
          sys.exit()
 elif total_nodes > nodes_needed:
    nodes_to_remove = ' '.join(['node%03d' % x for x in range(nodes_needed + 1, total_nodes)])
    nodes_command = "sudo starcluster rn %s stormseq_%s" % (nodes_to_remove, sample)
    exit_status = subprocess.call(nodes_command.split(' '), stdout=f)

clean_qsub = 'qsub -b y -cwd python clean.py --bam=/mydata/%(bam)s --dbsnp=%(dbsnp)s --reference=%(reference)s --platform=%(platform)s --covariates=%(covariates)s --chromosome=%(chromosome)s %(intervals)s'
call_qsub = 'qsub -hold_jid %(hold)s -b y -cwd python %(program)s-call.py --bam=/mydata/%(bam)s --dbsnp=%(dbsnp)s --reference=%(reference)s --chromosome=%(chromosome)s %(intervals)s %(indels)s'

f.write(clean_qsub + '\n' + call_qsub + '\n')
chroms = ['chr%s' % x for x in range(1,23)]
chroms.extend(['chrX', 'chrY', 'chrM'])

possible_covariates = 'ReadGroupCovariate,QualityScoreCovariate,CycleCovariate,DinucCovariate,HomopolymerCovariate'.split(',')

inputs = {
  'bam' : parameters['sample_name'] + '.merged.bam',
  'dbsnp' : dbsnp_paths[parameters['dbsnp_version']],
  'reference' : ref_paths[parameters['genome_version']],
  'platform' : 'Illumina',
  'covariates' : ','.join([x for x in possible_covariates if parameters[x]]),
  'program': parameters['calling_pipeline'],
  'intervals': '',
  'indels' : '--indels' if parameters['indel_calling'] else ''}

starcluster = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')

if parameters['data_type'] == 'type_exome_illumina':
  inputs['intervals'] = '--intervals=/data/intervals/Illumina_TruSeq.50bp.interval_list'
elif parameters['data_type'] == 'type_exome_custom':
  check_command = copy.deepcopy(starcluster)
  check_command.append("'ls -1 /mydata/*.interval_list'")
  stdout = subprocess.check_output(check_command)
  f.write(stdout + '\n')
  if stdout.find('interval_list') > -1:
    int_files = [line for line in stdout.split('\n') if line.find('interval_list') > -1]
    inputs['intervals'] = '--intervals=%s' % int_files[0]

if inputs['program'] == 'gatk':
    try:
        inputs['stand_call_conf'] = float(parameters['gatk-opt-std-call'])
    except ValueError:
        inputs['stand_call_conf'] = "30.0"
    try:
        inputs['stand_emit_conf'] = float(parameters['gatk-opt-std-emit'])
    except ValueError:
        inputs['stand_emit_conf'] = "30.0"
    call_qsub += ' --stand_call_conf=%(stand_call_conf)s --stand_emit_conf=%(stand_emit_conf)s'
    call_qsub += ' --call_all_dbsnp' if parameters['call-all-dbsnp'] else ''

all_clean_jobs = []
all_call_jobs = []
for chrom in chroms:
    inputs['chromosome'] = chrom
    
    # Cleaning
    chrom_job = copy.deepcopy(starcluster)
    chrom_job.append("'" + clean_qsub % inputs + "'")
    f.write(' '.join(chrom_job) + '\n')
    stdout = subprocess.check_output(chrom_job)
    job = get_job_id(stdout)
    f.write(stdout + '\n')
    all_clean_jobs.append(job)
    inputs['hold'] = job
    
    # SNP and Indel calling
    chrom_job = copy.deepcopy(starcluster)
    chrom_job.append("'" + call_qsub % inputs + "'")
    f.write(' '.join(chrom_job) + '\n')
    stdout = subprocess.check_output(chrom_job)
    job = get_job_id(stdout)
    f.write(stdout + '\n')
    all_call_jobs.append(job)
    
    # SV calling
    if parameters['sv_calling']:
      pass

priority = ','.join(chroms)
all_bams = ','.join(['/mydata/' + parameters['sample_name'] + '_' + chrom + '.recal.bam' for chrom in chroms])

merge_command = "sudo starcluster sshmaster stormseq_%s" % sample
merge_command += " 'qsub -hold_jid %s -b y -cwd -N mergef python merge.py --bams=%s --output=/mydata/%s'" % (','.join(all_clean_jobs), all_bams, parameters['sample_name'] + '.final.bam')
f.write(merge_command)
exit_status, stdout = commands.getstatusoutput(merge_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

merge_command = "sudo starcluster sshmaster stormseq_%s" % sample
merge_command += " 'qsub -hold_jid %s -b y -cwd touch /mydata/%s.done'" % (job, parameters['sample_name'] + '.final.bam.done')
f.write(merge_command)
exit_status, stdout = commands.getstatusoutput(merge_command)
f.write(stdout + '\n')

depth_command = "sudo starcluster sshmaster stormseq_%s" % sample
depth_command += " 'qsub -hold_jid %s -b y -cwd -N depth python depth.py --reference=%s --input=/mydata/%s.final.bam --output=/mydata/%s.depth'" % (job, ref_paths[parameters['genome_version']], parameters['sample_name'], parameters['sample_name'])
f.write(depth_command)
exit_status, stdout = commands.getstatusoutput(depth_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

priority = ','.join(chroms)
vcf_merge_command = "sudo starcluster sshmaster stormseq_%s" % sample
vcf_merge_command += " 'qsub -hold_jid %s -b y -cwd -N mergevs python merge-vcf.py --reference=%s --priority=%s --output=/mydata/%s'" % (','.join(all_call_jobs), ref_paths[parameters['genome_version']], priority, parameters['sample_name'] + '.vcf')
f.write(vcf_merge_command)
exit_status, stdout = commands.getstatusoutput(vcf_merge_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

vcf_stats_command = "sudo starcluster sshmaster stormseq_%s" % sample
vcf_stats_command += " 'qsub -hold_jid %s -b y -cwd -N vcfstats python vcf-stats.py %s --reference=%s --dbsnp=%s --input=/mydata/%s.vcf --output=/mydata/%s.vcf.eval'" % (job, inputs['intervals'], ref_paths[parameters['genome_version']], dbsnp_paths[parameters['dbsnp_version']], parameters['sample_name'], parameters['sample_name'])
f.write(vcf_stats_command)
exit_status, stdout = commands.getstatusoutput(vcf_stats_command)
job = get_job_id(stdout)
f.write(stdout + '\n')

time.sleep(60)
command = ['sudo', 'python', '/var/www/finish.py', config_file]
f.write(' '.join(command) + '\n')
p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
f.write('%s\n' % p.pid)
f.close()
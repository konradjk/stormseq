import time, json, sys, copy
import commands, subprocess

def get_job_id(input_string):
    lines = input_string.strip().split('\n')
    for line in lines:
        if line.find('has been submitted') > -1:
            return line.split()[2]
    return None

starcluster = "sudo starcluster sshmaster stormseq".split(' ')

f = open("/tmp/cleaning_log.txt","w")
parameters = json.loads(sys.argv[1])
f.write('Input is:\n%s\n' % '\n'.join(['%s:\t%s' % (x, parameters[x]) for x in parameters]))
f.flush()
check_command = copy.deepcopy(starcluster)
check_command.append("'qstat'")
stdout = subprocess.check_output(check_command)
f.write(stdout)
while len(stdout.split('\n')) > 5:
    stdout = subprocess.check_output(check_command)
    time.sleep(10)

def get_stats_file(parameters, ext, log):
    get_command = "sudo starcluster get stormseq".split(' ')
    stats_filename = "%s.%s" % (parameters['sample_name'], ext)
    get_command.append("/mydata/%s" % stats_filename)
    get_command.append("/var/www/%s" % stats_filename)
    stdout = subprocess.check_output(get_command)
    log.write(stdout + '\n')
    command = "tar zxv -C /var/www/ -f /var/www/%s" % stats_filename
    log.write(command + '\n')
    stdout = subprocess.check_output(command.split())
    log.write(stdout + '\n')

get_stats_file(parameters, 'merged.stats.tar.gz', f)

number_of_samples = 1
f.write('finished!\n')
ref_paths = { 'hg19' : '/data/hg19/hg19.fa',
              'ceu_ref' : '/data/ceu_ref/ceu_ref.fa',
              'hg18' : '/data/hg18/hg18.fa' }
dbsnp_paths = { 'dbsnp135' : '/data/dbsnp/dbsnp_135.vcf',
                'dbsnp132' : '/data/dbsnp/dbsnp_132.vcf' }

if parameters['alignment_pipeline'] == 'bwa':
    nodes_needed = 24*number_of_samples
elif parameters['alignment_pipeline'] == 'snap':
    nodes_needed = 4*number_of_samples
total_nodes = int(parameters['number_of_processes'])
f.write('have:\t%s nodes\nneed:\t%s nodes\n' % (total_nodes, nodes_needed))
f.flush()


if total_nodes < nodes_needed:
    nodes_to_add = nodes_needed - total_nodes
    nodes_names_to_add = ','.join(['node%03d' % x for x in range(total_nodes, nodes_needed)])
    nodes_command = "sudo starcluster an -n %s -a %s stormseq" % (nodes_to_add, nodes_names_to_add)
    output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
    f.write(output + '\n')
    while output.find('does not exist') > -1:
        time.sleep(300)
        nodes_command = "sudo starcluster an -x -n %s -a %s stormseq" % (nodes_to_add, nodes_names_to_add)
        output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
elif total_nodes > nodes_needed:
    nodes_to_remove = ' '.join(['node%03d' % x for x in range(nodes_needed + 1, total_nodes)])
    nodes_command = "sudo starcluster rn %s stormseq" % nodes_to_remove
    exit_status = subprocess.call(nodes_command.split(' '), stdout=f)
        
clean_qsub = 'qsub -b y -cwd python clean.py --bam=/mydata/%(bam)s --dbsnp=%(dbsnp)s --reference=%(reference)s --platform=%(platform)s --covariates=%(covariates)s --chromosome=%(chromosome)s'

call_qsub = 'qsub -hold_jid %(hold)s -b y -cwd python %(program)s-call.py --bam=/mydata/%(bam)s --dbsnp=%(dbsnp)s --reference=%(reference)s --chromosome=%(chromosome)s'
f.write(clean_qsub + '\n' + call_qsub + '\n')
chroms = ['chr%s' % x for x in range(1,23)]
chroms.extend(['chrX', 'chrY', 'chrM'])

possible_covariates = 'ReadGroupCovariate,QualityScoreCovariate,CycleCovariate,DinucCovariate,HomopolymerCovariate'.split(',')

inputs = { 'bam' : parameters['sample_name'] + '.merged.bam',
          'dbsnp' : dbsnp_paths[parameters['dbsnp_version']],
          'reference' : ref_paths[parameters['genome_version']],
          'platform' : 'Illumina',
          'covariates' : ','.join([x for x in possible_covariates if parameters[x]]),
          'program': parameters['calling_pipeline'] }
        
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
    
    # Variant calling
    chrom_job = copy.deepcopy(starcluster)
    chrom_job.append("'" + call_qsub % inputs + "'")
    f.write(' '.join(chrom_job) + '\n')
    stdout = subprocess.check_output(chrom_job)
    job = get_job_id(stdout)
    f.write(stdout + '\n')
    all_call_jobs.append(job)

priority = ','.join(chroms)
all_bams = ','.join(['/mydata/' + parameters['sample_name'] + '_' + chrom + '.recal.bam' for chrom in chroms])

vcf_merge_command = "sudo starcluster sshmaster stormseq 'qsub -hold_jid %s -b y -cwd python merge.py --bams=%s --output=/mydata/%s'" % (','.join(all_clean_jobs), all_bams, parameters['sample_name'] + '.final.bam')
exit_status, stdout = commands.getstatusoutput(vcf_merge_command)
f.write(stdout + '\n')

priority = ','.join(chroms)

vcf_merge_command = "sudo starcluster sshmaster stormseq 'qsub -hold_jid %s -b y -cwd python merge-vcf.py --reference=%s --priority=%s --output=/mydata/%s'" % (','.join(all_call_jobs), ref_paths[parameters['genome_version']], priority, parameters['sample_name'] + '.vcf')
exit_status, stdout = commands.getstatusoutput(vcf_merge_command)
f.write(stdout + '\n')

time.sleep(60)
p = subprocess.Popen(['python', '/root/finish.py', json.dumps(parameters)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
f.write('%s\n' % p.pid)
f.close()
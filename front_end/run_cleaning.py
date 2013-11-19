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

try:
	time.sleep(300)
	check_command = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
	check_command.append("'qstat'")
	stdout = subprocess.check_output(check_command)
	f.write('%s\nlength: %s\n' % (stdout, len(stdout.split('\n'))))
	while len(stdout.split('\n')) > 5:
		try:
			stdout = subprocess.check_output(check_command)
		except subprocess.CalledProcessError:
			pass
		time.sleep(300)
	
	get_stats_file(sample, sample + '.merged.stats.tar.gz', f)
	
	f.write('finished!\n')
	
	if parameters['data_type'].find('exome') > -1:
		n = 16/allowed_instances['bwa'][parameters['instance_type']]
	else:
		n = 24/allowed_instances['bwa'][parameters['instance_type']]
	nodes_needed = min(parameters['max_on_zone'], n)
	total_nodes = int(parameters['number_of_processes'])
	f.write('have:\t%s nodes\nneed:\t%s nodes\n' % (total_nodes, nodes_needed))
	f.flush()
	
	if True:
		if total_nodes < nodes_needed:
			nodes_to_add = nodes_needed - total_nodes
			nodes_names_to_add = ','.join(['node%03d' % x for x in range(total_nodes, nodes_needed)])
			try:
				nodes_command = "sudo timelimit -t 1800 -T 1 starcluster an -n %s -a %s stormseq_%s" % (nodes_to_add, nodes_names_to_add, sample)
				f.write(nodes_command + '\n')
				output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
				f.write(output + '\n')
				f.flush()
			except subprocess.CalledProcessError, e:
				f.write(str(e) + '\n')
				f.flush()
				time.sleep(120)
				try:
					# Try adding nodes again
					nodes_command = "sudo timelimit -t 1800 -T 1 starcluster an -x -n %s -a %s stormseq_%s" % (nodes_to_add, nodes_names_to_add, sample)
					f.write(nodes_command + '\n')
					output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
					f.write(output + '\n')
					f.flush()
				except subprocess.CalledProcessError, e:
					# Last ditch effort if add nodes fails
					f.write(str(e) + '\n')
					f.flush()
					time.sleep(120)
					for i in range(3):
						try:
							nodes_command = "sudo timelimit -t 1800 -T 1 starcluster terminate -c stormseq_%s" % (sample)
							f.write(nodes_command + '\n')
							output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
							f.write(output + '\n')
							f.flush()
							break
						except Exception, e:
							f.write('Failed to terminate cluster... Waiting 30 minutes and trying again...\n')
							f.flush()
							time.sleep(1800)
					try:
						nodes_command = "sudo timelimit -t 1800 -T 1 starcluster start -s %s --force-spot-master --cluster-template=stormseq_%s stormseq_%s" % (nodes_needed, sample, sample)
						f.write(nodes_command + '\n')
						output = subprocess.check_output(nodes_command.split(' '), stderr=subprocess.PIPE)
						f.write(output + '\n')
						f.flush()
					except subprocess.CalledProcessError, e:
						f.write('Something went wrong with the cluster...\n')
						sys.exit()
		elif total_nodes > nodes_needed:
			nodes_to_remove = ' '.join(['node%03d' % x for x in range(nodes_needed + 1, total_nodes)])
			nodes_command = "sudo starcluster rn %s stormseq_%s" % (nodes_to_remove, sample)
			exit_status = subprocess.call(nodes_command.split(' '), stdout=f)

	clean_qsub = 'qsub -b y -cwd -e /mydata/logs/ -o /mydata/logs/ -R y -l virtual_free=6400M python clean.py %(lite)s --bam=/mydata/%(bam)s --dbsnp=%(dbsnp)s --reference=%(reference)s --platform=%(platform)s --covariates=%(covariates)s --chromosome=%(chromosome)s %(intervals)s %(bad_cigar)s'
	call_qsub = 'qsub -hold_jid %(hold)s -e /mydata/logs/ -o /mydata/logs/ -b y -cwd -R y -l virtual_free=6400M python %(program)s-call.py %(lite)s --bam=/mydata/%(bam)s --dbsnp=%(dbsnp)s --reference=%(reference)s --chromosome=%(chromosome)s %(intervals)s %(indels)s'
	annotate_qsub = "qsub -hold_jid %(hold)s -e /mydata/logs/ -o /mydata/logs/ -b y -cwd -R y -l virtual_free=6400M python %(annotate_program)s-annotate.py --input=/mydata/%(sample)s_%(chromosome)s.raw.vcf --output=/mydata/%(sample)s_%(chromosome)s.vcf --chromosome=%(chromosome)s"
	
	f.write(clean_qsub + '\n' + call_qsub + '\n')
	chroms = get_chroms()
	
	possible_covariates = 'ReadGroupCovariate,QualityScoreCovariate,CycleCovariate,ContextCovariate'.split(',')
	
	threads_per_instance = {
		'm1.large' : 2,
		'm1.xlarge' : 4 if len(input['files']) == 1 else 2,
		'c1.xlarge' : 8
	}
	if len(input['files']) == 1:
		threads_per_instance['m2.4xlarge'] = 8
	elif len(input['files']) == 2:
		threads_per_instance['m2.4xlarge'] = 4
	else:
		threads_per_instance['m2.4xlarge'] = 2
	
	inputs = {
		'sample' : sample,
		'bam' : parameters['sample_name'] + '.merged.bam',
		'dbsnp' : dbsnp_paths[parameters['dbsnp_version']],
		'reference' : ref_paths[parameters['genome_version']],
		'platform' : 'Illumina',
		'covariates' : ','.join([x for x in possible_covariates if parameters[x]]),
		'program': parameters['calling_pipeline'],
		'annotate_program' : parameters['annotation_pipeline'],
		'intervals': '',
		'indels' : '--indels' if parameters['indel_calling'] else '',
		'bad_cigar' : '--bad_cigar' if parameters['alignment_pipeline'] == 'snap' else '',
		'threads': threads_per_instance[parameters['instance_type']],
		'lite': '--lite'
		#'lite': '--lite' if parameters['calling_pipeline'] == 'gatk-lite' else ''}
	}
	
	if parameters['calling_pipeline'] == 'gatk-lite':
		inputs['program'] = parameters['calling_pipeline'] = 'gatk'
	
	starcluster = ("sudo starcluster sshmaster stormseq_%s" % sample).split(' ')
	
	if parameters['data_type'] == 'type_exome_illumina':
		inputs['intervals'] = '--intervals=/data/intervals/Illumina_TruSeq.50bp.interval_list'
	elif parameters['data_type'] == 'type_exome_custom':
		# TODO: Add custom exome files
		check_command = copy.deepcopy(starcluster)
		check_command.append("'ls -1 /mydata/*.interval_list'")
		stdout = subprocess.check_output(check_command)
		f.write(stdout + '\n')
		if stdout.find('interval_list') > -1:
			int_files = [line for line in stdout.split('\n') if line.find('interval_list') > -1]
			inputs['intervals'] = '--intervals=%s' % int_files[0]
	
	if inputs['program'] == 'gatk':
		try:
			inputs['stand_call_conf'] = float(parameters['gatk_opt_std_call'])
		except ValueError:
			inputs['stand_call_conf'] = "30.0"
		try:
			inputs['stand_emit_conf'] = float(parameters['gatk_opt_std_emit'])
		except ValueError:
			inputs['stand_emit_conf'] = "30.0"
		call_qsub += ' --stand_call_conf=%(stand_call_conf)s --stand_emit_conf=%(stand_emit_conf)s'
		call_qsub += ' --output_gvcf' if parameters['output_gvcf'] else ''
	elif inputs['program'] == 'samtools':
		try:
			inputs['opt_d'] = int(parameters['samtools_opt_d'])
		except ValueError:
			inputs['opt_d'] = "100"
		call_qsub += ' --opt_d=%(opt_d)s'
		if inputs['intervals'] != '': inputs['intervals'] += '.bed'
	
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
		inputs['hold'] = job
		
		chrom_job = copy.deepcopy(starcluster)
		chrom_job.append("'" + annotate_qsub % inputs + "'")
		f.write(' '.join(chrom_job) + '\n')
		stdout = subprocess.check_output(chrom_job)
		job = get_job_id(stdout)
		f.write(stdout + '\n')
		all_call_jobs.append(job)
		
		# SV calling
		if parameters['sv_calling']:
			pass
	
	raw_command = "sudo starcluster sshmaster stormseq_%s 'qsub -b y -cwd -q all.q@master,all.q@node001 " % sample
	
	depth_command = raw_command + "-N depm python depth.py %s --reference=%s --input=/mydata/%s --output=/mydata/%s.merged.depth'" % (inputs['lite'], ref_paths[parameters['genome_version']], inputs['bam'], parameters['sample_name'])
	f.write(depth_command)
	exit_status, stdout = commands.getstatusoutput(depth_command)
	job = get_job_id(stdout)
	f.write(stdout + '\n')
	
	priority = ','.join(chroms)
	all_bams = ','.join(['/mydata/' + parameters['sample_name'] + '_' + chrom + '.recal.bam' for chrom in chroms])
	
	put_conf_file_command = 'sudo starcluster put stormseq_%s /root/.boto /root/.boto' % (sample)
	stdout = commands.getoutput(put_conf_file_command)
	put_conf_file_command = 'sudo starcluster put stormseq_%s --node node001 /root/.boto /root/.boto' % (sample)
	stdout = commands.getoutput(put_conf_file_command)
	
	final_bam = parameters['sample_name'] + '.final.bam'
	
	merge_command = raw_command + "-hold_jid %s -N mergef python merge.py --bams=%s --output=/mydata/%s'" % (','.join(all_clean_jobs), all_bams, final_bam)
	f.write(merge_command)
	exit_status, stdout = commands.getstatusoutput(merge_command)
	job = get_job_id(stdout)
	f.write(stdout + '\n')
	
	_, bucket_file = put_file_in_s3(parameters['sample_name'], 'final.bai', parameters['s3_bucket'], job)
	_, bucket_file = put_file_in_s3(parameters['sample_name'], 'final.stats.tar.gz', parameters['s3_bucket'], job)
	job, bucket_file = put_file_in_s3(parameters['sample_name'], 'final.bam', parameters['s3_bucket'], job)
	
	depth_command = raw_command + "-hold_jid %s -N depth python depth.py %s --reference=%s --input=/mydata/%s --output=/mydata/%s.depth'" % (job, inputs['lite'], ref_paths[parameters['genome_version']], final_bam, parameters['sample_name'])
	f.write(depth_command)
	exit_status, stdout = commands.getstatusoutput(depth_command)
	job = get_job_id(stdout)
	f.write(stdout + '\n')
	
	job, bucket_file = put_file_in_s3(parameters['sample_name'], 'depth.tar.gz', parameters['s3_bucket'], job)
	
	priority = ','.join(chroms)
	vcf_merge_command = raw_command +  "-hold_jid %s -N mergevs python merge-vcf.py %s --reference=%s --priority=%s --output=/mydata/%s'" % (','.join(all_call_jobs), inputs['lite'], ref_paths[parameters['genome_version']], priority, parameters['sample_name'] + '.vcf')
	f.write(vcf_merge_command)
	exit_status, stdout = commands.getstatusoutput(vcf_merge_command)
	vcf_job = get_job_id(stdout)
	f.write(stdout + '\n')
	
	_, bucket_file = put_file_in_s3(parameters['sample_name'], 'vcf', parameters['s3_bucket'], vcf_job)
	
	vcf_stats_command = raw_command + "-hold_jid %s -N vcfstats python vcf-stats.py %s --reference=%s --dbsnp=%s --input=/mydata/%s.vcf --output=/mydata/%s.vcf.eval'" % (vcf_job, inputs['intervals'], ref_paths[parameters['genome_version']], dbsnp_paths[parameters['dbsnp_version']], parameters['sample_name'], parameters['sample_name'])
	f.write(vcf_stats_command + '\n')
	exit_status, stdout = commands.getstatusoutput(vcf_stats_command)
	job = get_job_id(stdout)
	f.write(stdout + '\n')
	
	_, bucket_file = put_file_in_s3(parameters['sample_name'], 'vcf.eval', parameters['s3_bucket'], job)
	_, bucket_file = put_file_in_s3(parameters['sample_name'], 'vcf.snpden', parameters['s3_bucket'], job)
	
	time.sleep(60)
	command = ['sudo', 'python', '/var/www/finish.py', config_file]
	f.write(' '.join(command) + '\n')
	p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
	f.write('%s\n' % p.pid)
	f.close()
except Exception, e:
	print >> f, e
	f.flush()
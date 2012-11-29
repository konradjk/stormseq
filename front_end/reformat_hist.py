import sys

chroms = ['chr%s' % x for x in range(1,23)]
chroms.extend(['chrX', 'chrY'])
with open(sys.argv[1]) as f:
  f.readline()
  print '#chr\tstart\tend\tvalue'
  for line in f:
    fields = line.strip().split()
    if fields[0] in chroms:
      print '%s\t%s\t%s\t%s' % (fields[0].replace('chr', 'hs'), fields[1], int(fields[1]) + 1000000, float(fields[3])/1000)
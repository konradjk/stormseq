import sys
from optparse import OptionParser
from collections import defaultdict
import json
from helpers import *

parser = OptionParser()
parser.add_option('--input', help='VCF file')
parser.add_option('--sample')

(options, args) = parser.parse_args()

f = open(options.input)
results = defaultdict(lambda: defaultdict(int))
sifts = defaultdict(int)
polyphens = defaultdict(int)
for line in f:
  if line.find('#') == -1:
    #print line
    chrom, pos, id, ref, alt, qual, filter, info, format, ind = line.split()
    variant_type = 'known' if id.find('rs') > -1 else 'novel'
    info_dict = dict([x.split('=') if x.find('=') > -1 else (x, '') for x in info.split(';')])
    if 'CSQ' not in info_dict:
      continue
    types = set()
    for entry_text in info_dict['CSQ'].split(','):
      entry = entry_text.split('|')
      #Allele|Gene|Feature|Feature_type|Consequence|cDNA_position|CDS_position|Protein_position|Amino_acids|Codons|
      #Existing_variation|EXON|INTRON|MOTIF_NAME|MOTIF_POS|HIGH_INF_POS|MOTIF_SCORE_CHANGE|DISTANCE|SIFT|PolyPhen|
      #ENSP|DOMAINS|CELL_TYPE
      features = entry[4].split('&')
      for feature in features:
        types.add(feature)
    for entry_text in info_dict['CSQ'].split(','):
      entry = entry_text.split('|')
      sift = entry[18]
      polyphen = entry[19]
      if sift != '':
        sifts[sift.split('(')[0]] += 1
        polyphens[polyphen.split('(')[0]] += 1
        break
    for type in types:
      results[type]['all'] += 1
      results[type][variant_type] += 1
      if variant_type == 'novel' and 'known' not in results[type]: results[type]['known'] = 0
      if variant_type == 'known' and 'novel' not in results[type]: results[type]['novel'] = 0
f.close()

g = open(options.input + '.annotation_summary', 'w')
g.write(json.dumps({
  'annotations' : results,
  'sifts' : sifts,
  'polyphens' : polyphens
}))
g.close()

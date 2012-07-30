#!/usr/bin/env python
import cgi
import os, glob, sys
import commands
import cgitb; cgitb.enable()  # for troubleshooting
import datetime

redirect_url = "/"

f = open('/tmp/price.log', 'w')
pk = glob.glob('/root/pk-*pem')
cert = glob.glob('/root/cert-*pem')
if len(pk) > 0 and len(cert) > 0:
  os.environ['EC2_PRIVATE_KEY'] = pk[0]
  os.environ['EC2_CERT'] = cert[0]
else:
  print 'Content-Type: text/html'
  print
  sys.stdout.write('Error,Error')
  sys.exit()
f.write('here\n')

week_ago = (datetime.datetime.utcnow()-datetime.timedelta(7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
exit_status, price_info = commands.getstatusoutput('ec2-describe-spot-price-history -d Linux/UNIX -t m2.4xlarge -t m1.large -a us-east-1b -s %s' % week_ago)

current_prices = {}
max_prices = {}
for entry in price_info.split('\n'):
  fields = entry.strip().split()
  if fields[3] not in current_prices:
    current_prices[fields[3]] = fields[1]
    max_prices[fields[3]] = fields[1]
  if fields[1] > max_prices[fields[3]]:
    max_prices[fields[3]] = fields[1]

f.close()
print 'Content-Type: text/html'
print
sys.stdout.write('%.5s,%.5s' % (current_prices['m1.large'], current_prices['m2.4xlarge']))

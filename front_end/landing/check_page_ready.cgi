#!/usr/bin/env python
import cgi
import sys, urllib
import cgitb; cgitb.enable()  # for troubleshooting

redirect_url = "/"

form = cgi.FieldStorage()
site = form.getvalue('site')

try:
  x = urllib.urlopen('https://' + site).getcode()
  if str(x) == '200':
    print 'Content-Type: text/html'
    print
    sys.stdout.write('ready')
except IOError:
  print 'Content-Type: text/html'
  print
  sys.stdout.write('fail')

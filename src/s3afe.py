#!/usr/bin/env python
"""
S3afe stores a file on Amazon S3

The MIT License

Copyright (c) 2009 Fabian Topfstedt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import optparse, os, sys

try:
    from boto.exception import S3ResponseError
    from boto.s3.connection import S3Connection
except ImportError:
    sys.exit('Error: Please install boto first: "sudo easy_install boto"!')

def _get_envar_or_none(name):
    """
    Returns the environment variable with the given name or None.
    """
    if name in os.environ.keys():
        return os.environ[name]
    return None
    
def _upload(awskey, awssecret, filename, bucketname, keyname, acl):
    """
    Uploads a file to S3
    """
    try: 
        conn = S3Connection(awskey, awssecret)
        bucket = conn.get_bucket(bucketname)
        key = bucket.new_key(keyname)
        key.set_contents_from_filename(filename)
        key.set_acl(acl)
    except S3ResponseError, exc:
        if exc.status == 403:
            sys.exit('Error: Please check your Amazon credentials!')
        elif exc.status == 404:
            sys.exit('Error: Your bucket does not exist (yet)')
    else:
        print 'Upload successful! Your file is now s3afe!'

def main():
    """
    Main method parses the options and triggers the upload.
    """
    optparser = optparse.OptionParser(prog='s3afe.py', version='0.1',
        description='S3afe stores a file on Amazon S3',
        usage='%prog -k [access key id] -s [secret access key] ' + \
            '-b [bucketname] -n [keyname] -f [file]')
    optparser.add_option('--aws_access_key_id', '-k', dest='awskey', 
        default=_get_envar_or_none('AWS_ACCESS_KEY_ID'))
    optparser.add_option('--aws_secret_access_key', '-s', dest='awssecret', 
        default=_get_envar_or_none('AWS_SECRET_ACCESS_KEY'))
    optparser.add_option('--filename', '-f', dest='filename')
    optparser.add_option('--bucketname', '-b', dest='bucketname')
    optparser.add_option('--keyname', '-n', dest='keyname')
    optparser.add_option('--acl', '-a', dest='acl', default='private',
        choices=['private', 'public-read', 'public-read-write', 
        'authenticated-read'])
    options, arguments = optparser.parse_args()
    if options.awskey and options.awssecret and options.filename and \
        options.bucketname and options.keyname and options.acl:
        if not os.path.isfile(options.filename):
            sys.exit('Error: The file does not exist!')
        _upload(options.awskey, options.awssecret, options.filename, 
            options.bucketname, options.keyname, options.acl)
    else:
        optparser.print_help()

if __name__ == '__main__':
    main()
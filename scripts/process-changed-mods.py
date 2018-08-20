#!/usr/bin/env python
#
# Copyright (c) 2017  Joe Clarke <jclarke@cisco.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

# Typically called once per minute via a cron job with arguments:
#  --time -1
#  --dbf ${DBF}
#
# The 2nd argument is not more usefull as MySQL is used rather than SQLite
#

import json
import sys
import os
import argparse
from subprocess import call
import MySQLdb

mod_list = {}
find_args = []
del_list = []

parser = argparse.ArgumentParser(
    description="Process changed modules in a git repo")
parser.add_argument('--time', type=str,
                    help='Modified time argument to find(1)', required=False)
parser.add_argument('--dbf', type=str,
                    help='Path to the database file', required=True)
args = parser.parse_args()

if args.time:
    find_args = ['-f', args.time]

try:
    if os.path.getsize(os.environ['YANG_CACHE_FILE']) > 0:
        fd = open(os.environ['YANG_CACHE_FILE'], 'r+')
        mod_list = json.load(fd)

        # Backup the contents just in case.
        bfd = open(os.environ['YANG_CACHE_FILE'] + '.bak', 'w')
        json.dump(mod_list, bfd)
        bfd.close()

        # Zero out the main file.
        fd.seek(0)
        fd.truncate()
        fd.close()
except Exception as e:
    print('Failed to read cache file {}'.format(e))
    mod_list = {}

try:
    if os.path.getsize(os.environ['YANG_DELETE_FILE']) > 0:
        fd = open(os.environ['YANG_DELETE_FILE'], 'r+')
        del_list = json.load(fd)

        # Backup the contents just in case.
        bfd = open(os.environ['YANG_DELETE_FILE'] + '.bak', 'w')
        json.dump(del_list, bfd)
        bfd.close()

        # Zero out the main file.
        fd.seek(0)
        fd.truncate()
        fd.close()
except Exception as e:
    print('Failed to read delete cache file {}'.format(e))
    del_list = []

if len(del_list) > 0:
    try:
        con = MySQLdb.connect(host="localhost",  # your host, usually localhost
                               user="yang",  # your username
                               passwd="Y@ng3r123",  # your password
                               db="yang")  # name of the data base
        cur = con.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        for mod in del_list:
            mname = mod.split('@')[0]
            mrev_org = mod.split('@')[1]
            mrev = mrev_org.split('/')[0]
            morg = '/'.join(mrev_org.split('/')[1:])
            sql = 'DELETE FROM modules WHERE module=%(mod)s AND revision=%(rev)s AND organization=%(org)s'
            try:
                cur.execute(sql, {'mod': mname, 'rev': mrev,
                                  'org': morg})
                sql = 'DELETE FROM yindex WHERE module=$(mod)s AND revision=%(rev)s AND organization=%(org)s'
                cur.execute(sql, {'mod': mname, 'rev': mrev,
                                  'org': morg})
            except MySQLdb.Error as e:
                print('Failed to delete {} from the index: {}'.format(
                    mod, e.args[0]))
        con.commit()
        con.close()
    except MySQLdb.Error as e:
        print("Error connecting to DB: {}".format(e.args[0]))

if len(mod_list) == 0:
    sys.exit(0)

mod_args = []
if type(mod_list) is list:
    for mod_path in mod_list:
        if not mod_path.startswith('/'):
            mod_path = os.environ['YANGDIR'] + '/' + mod_path
        mod_args.append(mod_path)
else:
    for m, mod_path in mod_list.items():
        mparts = m.split('/')
        if len(mparts) == 2:
            mod_path += ':' + mparts[1]
        if not mod_path.startswith('/'):
            mod_path = os.environ['YANGDIR'] + '/' + mod_path
        mod_args.append(mod_path)

args = ['./build_yindex.sh'] + find_args + mod_args

os.chdir(os.environ['TOOLS_DIR'])
call(args)

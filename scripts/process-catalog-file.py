#!/usr/bin/env python

#
# Copyright The IETF Trust 2019, All Rights Reserved
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

import MySQLdb
import re
import os
import sys
import json

if len(sys.argv) != 7:
    print("Usage: {} <Catalog file> <DB file> <YDEP_DIR>".format(sys.argv[0]))
    sys.exit(1)

catf = sys.argv[1]
dbname = sys.argv[2]
YDEP_DIR = sys.argv[3]
host = sys.argv[4]
user = sys.argv[5]
passwd = sys.argv[6]

catalog = None

try:
    fd = open(catf, 'r')
    catalog = json.load(fd)
    fd.close()
except Exception as e:
    print('Failed to parse catalog file {}: "{}"'.format(catf, e.args[0]))
    sys.exit(1)

try:
    con = MySQLdb.connect(host=host,  # your host, usually localhost
                          user=user,  # your username
                          passwd=passwd,  # your password
                          db=dbname)  # name of the data base
except MySQLdb.Error as e:
    print("Error connecting to DB: {}".format(e.args[0]))
    sys.exit(1)

# DB schema:
# CREATE TABLE modules(module, revision, belongs_to, namespace, prefix,
# organization, maturity, document, file_path);

for organization in catalog['openconfig-module-catalog:organizations']['organization']:
    oname = organization['name']
    if oname == 'ietf' or oname == 'iana':
        # We handle the IETF separately.
        continue

    for module in organization['modules']['module']:
        mname = module['name']
        revision = module['revision']
        prefix = module['prefix']
        namespace = module['namespace']

        # Normalize organizations
        moname = oname
        m = re.search(r"urn:([^:]+):", namespace)
        if m:
            moname = m.group(1)

        belongs_to = ''
        if 'module-hierarchy' in module and 'module-parent' in module['module-hierarchy']:
            belongs_to = module['module-hierarchy']['module-parent']
        if 'dependencies' in module and 'required-module' in module['dependencies']:
            try:
                dep_file = '{}/{}.json'.format(YDEP_DIR, mname)
                if not os.path.exists(dep_file):
                    fd = open(dep_file, 'w')
                    ydep = {}
                    ydep['impacting_modules'] = {}
                    ydep['impacting_modules'][mname] = module[
                        'dependencies']['required-module']
                    ydep['impacted_module'] = {}
                    json.dump(ydep, fd, indent=4)
                    fd.close()
            except Exception as e:
                print("Failed to dump dependencies for {}: {}".format(
                    mname, e.args[0]))
        document = ''
        if 'document' in module:
            reg = re.compile(r'(<a.*?>(.*?)</a>)', re.S | re.M)
            match = reg.match(module['document'])
            if match:
                document = match.groups()[1].strip(
                ) + '|' + match.groups()[0].strip()
            else:
                reg = re.compile(r'([\w\-\.]*)[^<]+<([^>]+)>', re.S | re.M)
                match = reg.search(module['document'])
                if match:
                    document = match.groups()[0].strip(
                    ) + '|' + '<a href="{}">{}</a>'.format(match.groups()[1].strip(), match.groups()[0].strip())
                else:
                    document = module['document']
        file_path = ''

        maturity = ''
        if 'maturity' in module:
            maturity = module['maturity']

        yang_version = '1.0'
        if 'yang-version' in module:
            yang_version = module['yang-version']

        sql = 'UPDATE modules SET maturity = %(mat)s, document = %(doc)s WHERE module = %(mod)s AND revision = %(rev)s'
        try:
            cur.execute(sql, {'mod': mname, 'rev': revision,
                              'mat': maturity, 'doc': document})
        except MySQLdb.Error as e:
            print('Failed to update module data for {}: {}'.format(
                mname, e.args[0]))
            continue

        if cur.rowcount == 0:
            sql = 'INSERT INTO modules (module, revision, yang_version, belongs_to, namespace, prefix, organization, maturity, document, file_path) VALUES (%(mod)s, %(rev)s, %(yver)s, %(bt)s, %(ns)s, %(prefix)s, %(org)s, %(mat)s, %(doc)s, %(fp)s)'
            try:
                cur.execute(sql, {'mod': mname, 'rev': revision, 'yver': yang_version, 'bt': belongs_to, 'ns': namespace,
                                  'prefix': prefix, 'org': moname, 'mat': maturity, 'doc': document, 'fp': file_path})
            except MySQLdb.Error as e:
                print('Failed to insert new module data for {}: {}'.format(
                    mname, e.args[0]))
                continue

con.commit()
con.close()

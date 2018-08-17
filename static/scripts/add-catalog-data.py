#!/usr/bin/env python
#
# Copyright (c) 2016-2017  Joe Clarke <jclarke@cisco.com>
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
import requests
import re
import os
import sys

# Script should be called with the following arguments
# dbname, host, user, passwd

if len(sys.argv) != 5:
    print("Usage: {} <DB file>".format(sys.argv[0]))
    sys.exit(1)

dbname = sys.argv[1]
host = sys.argv[2]
user = sys.argv[3]
passwd = sys.argv[4]

# Map propietary namespaces to known org strings.
NS_MAP = {
    "http://cisco.com/": "cisco",
    "http://www.huawei.com/netconf": "huawei",
    "http://openconfig.net/yang": "openconfig",
    "http://tail-f.com/": "tail-f"
}

mods = {}

MATURITY_MAP = {
    "RFC": "http://www.claise.be/IETFYANGRFC.json",
    "DRAFT": "http://www.claise.be/IETFYANGDraft.json"
}

for m, u in MATURITY_MAP.items():
    try:
        r = requests.request("GET", u)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Error fetching JSON data from {}: {}".format(u, e.args[0]))
        sys.exit(1)

    j = r.json()

    for mod, props in j.items():
        mod = os.path.splitext(mod)[0]
        mods[mod] = {}

        reg = re.compile(r'<a.*?>(.*?)</a>', re.S | re.M)
        doc_tag = props
        mods[mod]['cstatus'] = ''
        if isinstance(props, list):
            doc_tag = props[0]
        match = reg.match(doc_tag)
        if match:
            mods[mod]['document'] = match.groups()[0].strip()
            mods[mod]['doc_url'] = doc_tag
            if m == 'DRAFT':
                if re.search(r'^draft-ietf-', mods[mod]['document']):
                    mods[mod]['maturity'] = 'WG DRAFT'
                else:
                    mods[mod]['maturity'] = 'INDIVIDUAL DRAFT'
                if isinstance(props, list):
                    mods[mod]['cstatus'] = props[3]
            else:
                mods[mod]['maturity'] = m
        else:
            mods[mod]['document'] = ''
            if m == 'DRAFT':
                mods[mod]['maturity'] = 'UNKNOWN'
            else:
                mods[mod]['maturity'] = m

try:
    con = MySQLdb.connect(host=host,  # your host, usually localhost
                           user=user,  # your username
                           passwd=passwd,  # your password
                           db=dbname)  # name of the data base
    cur = con.cursor(cursorclass=MySQLdb.cursors.DictCursor)
except MySQLdb.Error as e:
    print("Error connecting to DB: {}".format(e.args[0]))
    sys.exit(1)

for modn, props in mods.items():
    mod_parts = modn.split('@')
    mod = mod_parts[0]
    rev = ''
    if len(mod_parts) == 2:
        rev = mod_parts[1]
    
    sql = 'UPDATE modules SET maturity= %(maturity)s, document=%(document)s, compile_status=%(cstatus)s WHERE module=:%(modn)s'
    params = {'maturity': props['maturity'],
              'document': props['document'] + '|' + props['doc_url'], 'cstatus': props['cstatus'], 'modn': mod}
    if rev != '':
        sql += ' AND revision=%(rev)s'
        params['rev'] = rev
    try:
        cur.execute(sql, params)
    except MySQLdb.Error as e:
        print("Failed to update module maturity for {}: {}".format(
            modn, e.args[0]))

for ns, org in NS_MAP.items():
    sql = 'UPDATE modules SET organization=%(org)s WHERE namespace LIKE %(ns)s'
    try:
        cur.execute(sql, {'org': org, 'ns': ns + '%'})
    except MySQLdb.Error as e:
        print("Failed to update namespace data for {} => {}: {}".format(
            ns, org, e.args[0]))

con.commit()
con.close()

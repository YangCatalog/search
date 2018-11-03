# Copyright 2018 Cisco and its affiliates
#
# Licensed under the Apache Licparse_allense, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re

from scripts.listWriter import ListWriter

__author__ = "Miroslav Kovac and Joe Clarke"
__copyright__ = "Copyright 2018 Cisco and its affiliates"
__license__ = "Apache License, Version 2.0"
__email__ = "miroslav.kovac@pantheon.tech, jclarke@cisco.com"

import os
import subprocess
import MySQLdb
import MySQLdb.cursors
from pyang.plugins.json_tree import emit_tree
from pyang.plugins.name import emit_name
from pyang.plugins.yang_catalog_index import IndexerPlugin

from scripts.add_catalog_data import add_data
from scripts.yangParser import create_context


def __create_connection(dbHost, dbPass, dbName, dbUser):
    connection = MySQLdb.connect(host=dbHost,  # your host, usually localhost
                           user=dbUser,  # your username
                           passwd=dbPass,  # your password
                           db=dbName)  # name of the data base
    cursor = connection.cursor(cursorclass=MySQLdb.cursors.DictCursor)
    return connection, cursor


def __run_pyang_commands(commands, output_only=True, decode=True):
    pyang_args = ['pyang']
    pyang_args.extend(commands)
    pyang = subprocess.Popen(pyang_args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    stdout, stderr = pyang.communicate()
    if decode:
        stdout = stdout.decode(encoding='utf-8', errors='strict')
        stderr = stderr.decode(encoding='utf-8', errors='strict')
    if output_only:
        return stdout
    else:
        return stdout, stderr


def __run_query(query, cur):
    cur.execute(query)


def build_yindex(private_secret, ytree_dir, modules, yang_models,
                 dbHost, dbPass, dbName, dbUser, lock_file_cron,
                 my_uri, LOGGER, save_file_dir):
    conn, cur = __create_connection(dbHost, dbPass, dbName, dbUser)
    try:
        LOGGER.info('Creating temporary tables')
        cur.execute("CREATE TABLE yindex_temp LIKE yindex")
        cur.execute("CREATE TABLE modules_temp LIKE modules")
        cur.execute("INSERT yindex_temp SELECT * FROM yindex")
        cur.execute("INSERT modules_temp SELECT * FROM modules")
        LOGGER.info('Temporary tables created')
        x = 0
        for module in modules:
            x += 1
            LOGGER.info('yindex on module {}. module {} out of {}'.format(module.split('/')[-1], x, len(modules)))
            # split to module with path and organization
            m_parts = module.split(":")
            org = None
            if len(m_parts) > 1:
                m = m_parts[0]
                org = m_parts[1]
            else:
                m = m_parts[0]
            ctx = create_context('{}:{}'.format(yang_models, save_file_dir))
            with open(m, 'r') as f:
                 a = ctx.add_module(m, f.read())
            if a is None:
                LOGGER.warning('Unable to pyang parse module {} skipping this module'.format(module))
                continue
            with open('temp.txt', 'w') as f:
                ctx.opts.print_revision = True
                emit_name(ctx, [a], f)
            with open('temp.txt', 'r') as f:
                name_revision = f.read().strip()
            outputList = ListWriter()
            ctx.opts.yang_index_make_module_table = True
            ctx.opts.yang_index_no_schema = True
            plugin = IndexerPlugin()
            plugin.emit(ctx,[a], outputList)

            os.unlink('temp.txt')

            name_revision = name_revision.split('@')
            if len(name_revision) > 1:
                name = name_revision[0]
                revision = name_revision[1]
            else:
                name = name_revision[0]
                revision = '1970-01-01'
            cur.execute("DELETE FROM modules_temp WHERE module=%s AND revision=%s", (name, revision,))
            cur.execute("DELETE FROM yindex_temp WHERE module=%s AND revision=%s", (name, revision,))
            #yindex_insert_intos = yindex.replace('INSERT INTO', 'insert into')
            # TODO line below does not handle multi-line insert into statements
            #yindex_insert_intos = re.findall(r'((insert into).*?(\);[\r\n]+))', yindex_insert_intos, re.MULTILINE)
            for yindex_insert_into in outputList.getOutputList():
                insert = yindex_insert_into.replace('INSERT INTO', 'insert into')
                insert = insert.replace('insert into modules', 'INSERT INTO modules_temp')
                insert = insert.replace('insert into yindex', 'INSERT INTO yindex_temp')
                LOGGER.info('Executing: ' + insert)
                cur.execute(insert)
            cur.execute("UPDATE modules_temp SET file_path=%s WHERE module=%s AND revision=%s", (m, name, revision,))
            if org is not None:
                cur.execute("UPDATE modules_temp SET organization=%s WHERE module=%s AND revision=%s", (org, name, revision,))
                cur.execute("UPDATE yindex_temp SET organization=%s WHERE module=%s AND revision=%s", (org, name, revision,))

            with open('{}/{}@{}'.format(ytree_dir, name, revision), 'w') as f:
                emit_tree([a], f, ctx)
        add_data(conn, cur, private_secret, my_uri, LOGGER, lock_file_cron)
        try:
            LOGGER.info('Commiting changes into SQL database') 
            conn.commit()
        except Exception as e:
            # Rollback in case there is any error
            cur.execute("DROP TABLE yindex_temp")
            cur.execute("DROP TABLE modules_temp")
            os.unlink(lock_file_cron)
            conn.rollback()
            LOGGER.info('Failed to commit the changes')
            raise e
        LOGGER.info('Changes committed') 
        cur.execute("RENAME TABLE modules TO modules_remove")
        cur.execute("RENAME TABLE modules_temp TO modules")
        cur.execute("RENAME TABLE yindex TO yindex_remove")
        cur.execute("RENAME TABLE yindex_temp TO yindex")
        cur.execute("DROP TABLE yindex_remove")
        cur.execute("DROP TABLE modules_remove")
    except Exception as e:
        cur.execute("DROP TABLE yindex_temp")
        cur.execute("DROP TABLE modules_temp")
        os.unlink(lock_file_cron)
        conn.rollback()
        raise e


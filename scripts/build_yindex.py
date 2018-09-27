import os
import subprocess
import MySQLdb
import MySQLdb.cursors
from scripts import add_catalog_data
from scripts.add_catalog_data import add_data


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
                 my_uri, LOGGER):
    conn, cur = __create_connection(dbHost, dbPass, dbName, dbUser)
    try:
        cur.execute("""create table yindex_temp as select * from yindex""")
        cur.execute("""create table modules_temp as select * from modules""")
        x = 0
        for module in modules:
            x += 1
            LOGGER.info('yindex on module {}. module {} out of {}'.format(module.split('/')[-1], x, len(modules)))
            # split to module with path and organization
            m_parts = module.split(":")
            m = m_parts[0]
            org = m_parts[1]

            pyang_args = ['-p', yang_models, '-f', 'yang-catalog-index',
                          '--yang-index-make-module-table', '--yang-index-no-schema',
                          m]
            yindex = __run_pyang_commands(pyang_args, decode=False)

            pyang_args = ['-p', yang_models, '--name-print-revision', '-f',
                          'name', m]
            name_revision = __run_pyang_commands(pyang_args).strip()
            name, revision = name_revision.split('@')
            cur.execute("""DELETE FROM modules_temp WHERE module=%s AND revision=%s""", (name, revision,))
            cur.execute("""DELETE FROM yindex_temp WHERE module=%s AND revision=%s""", (name, revision,))
            yindex_insert_intos = yindex.split(b'\n')
            for yindex_insert_into in yindex_insert_intos:
                yindex_insert_into = yindex_insert_into.replace(b'INSERT INTO', b'insert into')
                if yindex_insert_into.startswith(b'insert into'):
                    if yindex_insert_into.startswith(b'insert into modules'):
                        yindex_insert_into = yindex_insert_into.replace(b"'", b'"')
                    yindex_insert_into = yindex_insert_into.decode(encoding='utf-8', errors='strict')
                    yindex_insert_into = yindex_insert_into.replace('insert into modules', 'insert into modules_temp')
                    yindex_insert_into = yindex_insert_into.replace('insert into yindex', 'insert into yindex_temp')
                    cur.execute(yindex_insert_into)
            cur.execute("""UPDATE modules_temp SET file_path=%s WHERE module=%s AND revision=%s""", (m, name, revision,))
            cur.execute("""UPDATE modules_temp SET organization=%s WHERE module=%s AND revision=%s""", (org, name, revision,))
            cur.execute("""UPDATE yindex_temp SET organization=%s WHERE module=%s AND revision=%s""", (org, name, revision,))
            pyang_args = ['-p', yang_models, '-f',
                          'json-tree', '-o',
                          '{}/{}@{}'.format(ytree_dir, name, revision), m]
            __run_pyang_commands(pyang_args)
        add_data(conn, cur, private_secret, my_uri, LOGGER, lock_file_cron)
        try:
            conn.commit()
        except Exception as e:
            # Rollback in case there is any error
            cur.execute("""drop table yindex_temp""")
            cur.execute("""drop table modules_temp""")
            os.unlink(lock_file_cron)
            conn.rollback()
            raise e
        cur.execute("""rename table modules to modules_remove""")
        cur.execute("""rename table modules_temp to modules""")
        cur.execute("""rename table yindex to yindex_remove""")
        cur.execute("""rename table yindex_temp to yindex""")
        cur.execute("""drop table yindex_remove""")
        cur.execute("""drop table modules_remove""")
    except Exception as e:
        cur.execute("""drop table yindex_temp""")
        cur.execute("""drop table modules_temp""")
        os.unlink(lock_file_cron)
        conn.rollback()
        raise e
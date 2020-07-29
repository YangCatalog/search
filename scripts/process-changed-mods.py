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

# Typically called once per minute via a cron job with arguments:
#  --time -1
#  --dbf ${DBF}
#
# The 2nd argument is not more usefull as MySQL is used rather than SQLite
#
import argparse
import configparser
import json
import logging
import os
import stat
import sys
import dateutil.parser

from elasticsearch import Elasticsearch, NotFoundError
from git import Repo
from git.cmd import Git

from scripts import build_yindex

__author__ = "Miroslav Kovac, Joe Clarke"
__copyright__ = "Copyright 2018 Cisco and its affiliates"
__license__ = "Apache License, Version 2.0"
__email__ = "miroslav.kovac@pantheon.tech, jclarke@cisco.com"


def get_logger(name, file_name_path='yang.log'):
    """Create formated logger with name of file yang.log
        Arguments:
            :param file_name_path: filename and path where to save logs.
            :param name :  (str) Set name of the logger.
            :return a logger with the specified name.
    """
    # check if file exists
    exists = False
    if os.path.isfile(file_name_path):
        exists = True
    FORMAT = '%(asctime)-15s %(levelname)-8s %(name)5s => %(message)s - %(lineno)d'
    DATEFMT = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(datefmt=DATEFMT, format=FORMAT, filename=file_name_path, level=logging.DEBUG)
    logger = logging.getLogger(name)
    # if file didn t exist we create it and now we can set chmod
    if not exists:
        os.chmod(file_name_path, 0o664 | stat.S_ISGID)
    return logger


def pull(repo_dir):
    """
    Pull all the new files in the master in specified directory.
    Directory should contain path where .git file is located.
    :param repo_dir: directory where .git file is located
    """
    g = Git(repo_dir)
    g.pull()
    a = Repo(repo_dir)
    for s in a.submodules:
        s.update(recursive=True, init=True)


if __name__ == '__main__':
    #find_args = []

    parser = argparse.ArgumentParser(
        description="Process changed modules in a git repo")
    parser.add_argument('--time', type=str,
                        help='Modified time argument to find(1)', required=False)
    parser.add_argument('--config-path', type=str, default='/etc/yangcatalog/yangcatalog.conf',
                        help='Set path to config file')
    args = parser.parse_args()
    config_path = args.config_path
    config = configparser.ConfigParser()
    config._interpolation = configparser.ExtendedInterpolation()
    config.read(config_path)
    log_directory = config.get('Directory-Section', 'logs')
    LOGGER = get_logger('process_changed_mods', log_directory + '/process-changed-mods.log')
    LOGGER.info('Initializing script loading config parameters')
    dbHost = config.get('DB-Section', 'host')
    dbName = config.get('DB-Section', 'name-search')
    dbUser = config.get('DB-Section', 'user')
    dbPass = config.get('Secrets-Section', 'mysql-password')
    es_host = config.get('DB-Section', 'es-host')
    es_port = config.get('DB-Section', 'es-port')
    es_protocol = config.get('DB-Section', 'es-protocol')
    my_uri = config.get('Web-Section', 'confd-ip')
    yang_models = config.get('Directory-Section', 'yang-models-dir')
    changes_cache_dir = config.get('Directory-Section', 'changes-cache')
    failed_changes_cache_dir = config.get('Directory-Section', 'changes-cache-failed')
    delete_cache_dir = config.get('Directory-Section', 'delete-cache')
    temp_dir = config.get('Directory-Section', 'temp')
    lock_file = config.get('Directory-Section', 'lock')
    lock_file_cron = config.get('Directory-Section', 'lock-cron')
    ytree_dir = config.get('Directory-Section', 'json-ytree')
    save_file_dir = config.get('Directory-Section', 'save-file-dir')
    threads = config.get('General-Section', 'threads')
    processes = int(config.get('General-Section', 'yProcesses'))
    recursion_limit = sys.getrecursionlimit()
    if os.path.exists(lock_file) or os.path.exists(lock_file_cron):
        # we can exist since this is run by cronjob every minute of every day
        LOGGER.warning('Temporary lock file used by something else. Exiting script !!!')
        sys.exit()
    try:
        open(lock_file, 'w').close()
        open(lock_file_cron, 'w').close()
    except:
        os.unlink(lock_file)
        os.unlink(lock_file_cron)
        LOGGER.error('Temporary lock file could not be created although it is not locked')
        sys.exit()

    changes_cache = {}
    delete_cache = []
    if ((not os.path.exists(changes_cache_dir) or os.path.getsize(changes_cache_dir) <= 0)
            and (not os.path.exists(delete_cache_dir) or os.path.getsize(delete_cache_dir) <= 0)):
        LOGGER.info('No new modules are added or removed. Exiting script!!!')
        os.unlink(lock_file)
        os.unlink(lock_file_cron)
        sys.exit()
    else:
        if os.path.exists(changes_cache_dir) and os.path.getsize(changes_cache_dir) > 0:
            LOGGER.info('Loading changes cache')
            f = open(changes_cache_dir, 'r+')
            changes_cache = json.load(f)

            # Backup the contents just in case.
            bfd = open(changes_cache_dir + '.bak', 'w')
            json.dump(changes_cache, bfd)
            bfd.close()

            f.truncate(0)
            f.close()

        if os.path.exists(delete_cache_dir) and os.path.getsize(delete_cache_dir) > 0:
            LOGGER.info('Loading delete cache')
            f = open(delete_cache_dir, 'r+')
            delete_cache = json.load(f)

            # Backup the contents just in case.
            bfd = open(delete_cache_dir + '.bak', 'w')
            json.dump(delete_cache, bfd)
            bfd.close()

            f.truncate(0)
            f.close()
        os.unlink(lock_file)

    if len(delete_cache) > 0:
        es = Elasticsearch([{'host': '{}'.format(es_host), 'port': es_port}])
        initialize_body_yindex = json.load(open('json/initialize_yindex_elasticsearch.json', 'r'))
        initialize_body_modules = json.load(open('json/initialize_module_elasticsearch.json', 'r'))

        es.indices.create(index='yindex', body=initialize_body_yindex, ignore=400)
        es.indices.create(index='modules', body=initialize_body_modules, ignore=400)

        logging.getLogger('elasticsearch').setLevel(logging.ERROR)

        for mod in delete_cache:
            mname = mod.split('@')[0]
            mrev_org = mod.split('@')[1]
            mrev = mrev_org.split('/')[0]
            morg = '/'.join(mrev_org.split('/')[1:])

            try:
                dateutil.parser.parse(mrev)
            except ValueError as e:
                if mrev[-2:] == '29' and mrev[-5:-3] == '02':
                    mrev = mrev.replace('02-29', '02-28')
                else:
                    mrev = '1970-01-01'

            try:
                query = \
                    {
                        "query": {
                            "bool": {
                                "must": [{
                                    "match_phrase": {
                                        "module.keyword": {
                                            "query": mname
                                        }
                                    }
                                }, {
                                    "match_phrase": {
                                        "revision": {
                                            "query": mrev
                                        }
                                    }
                                }]
                            }
                        }
                    }
                es.delete_by_query(index='yindex', body=query, doc_type='modules', conflicts='proceed',
                                   request_timeout=40)
                query['query']['bool']['must'].append({
                                    "match_phrase": {
                                        "organization": {
                                            "query": morg
                                        }
                                    }
                                })
                LOGGER.info('deleting {}'.format(query))
                es.delete_by_query(index='modules', body=query, doc_type='modules', conflicts='proceed',
                                   request_timeout=40)
            except NotFoundError as e:
                LOGGER.warning('module not found {}'.format(e))
                pass

    if len(changes_cache) == 0:
        LOGGER.info("No module to be processed. Exiting.")
        os.unlink(lock_file_cron)
        sys.exit(0)

    LOGGER.info('Pulling latest yangModels/yang repository')
    pull(yang_models)

    mod_args = []
    if type(changes_cache) is list:
        for mod_path in changes_cache:
            if not mod_path.startswith('/'):
                mod_path = yang_models + '/' + mod_path
            mod_args.append(mod_path)
    else:
        for m, mod_path in changes_cache.items():
            mparts = m.split('/')
            if len(mparts) == 2:
                mod_path += ':' + mparts[1]
            if not mod_path.startswith('/'):
                mod_path = yang_models + '/' + mod_path
            mod_args.append(mod_path)
    sys.setrecursionlimit(50000)
    build_yindex.build_yindex(ytree_dir, mod_args, LOGGER, save_file_dir,
                              es_host, es_port, es_protocol, threads,
                              log_directory + '/process-changed-mods.log', failed_changes_cache_dir,
                              temp_dir, processes)
    sys.setrecursionlimit(recursion_limit)
    os.unlink(lock_file_cron)
    LOGGER.info("Job finished successfully")

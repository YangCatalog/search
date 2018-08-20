#!/usr/bin/env bash
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

# This script uses pyang to build an SQLite3 index of YANG modules
# and nodes, as well as pyang and symd to build JSON files containing
# tree and dependency structures for YANG modules.
#

# The file yindex.env must be sourced into the environment prior to running
# this script.

update_progress() {
    mtotal=$1
    cur_mod=$2
    mcur=$3

    perc=$(bc -l <<< "scale=2; (${mcur} / ${mtotal}) * 100")

    echo "Processing module ${cur_mod} (${mcur} of ${mtotal} [${perc}%])"
}

if [ -z "${YANG_INDEX_HOME}" ]; then
    echo "ERROR: YANG_INDEX_HOME environment variable not defined; please set this to the path to the yindex.env file"
    exit 1
fi

. ${YANG_INDEX_HOME}/yindex.env

alias mysq="mysql -u ${USER} -p${PASSWD} ${DBNAME}"

#TDBF=$(mktemp -q)

mkdir -p ${YTREE_DIR}
mkdir -p ${YDEP_DIR}

if [ -n "${YANG_EXPLORER_DIR}" ]; then
    mkdir -p "${YANG_EXPLORER_DIR}/server/data/users/guest/yang"
    mkdir -p "${YANG_EXPLORER_DIR}/server/data/users/guest/cxml"
fi

if [ -z "${DRAFTS_DIR}" ]; then
    DRAFTS_DIR=${YANGDIR}
fi

if [ -z "${RFCS_DIR}" ]; then
    RFCS_DIR=${YANGDIR}
fi

if [ -z "${YANGREPO}" ]; then
    YANGREPO=${YANGDIR}
fi

if [ ${update_yang_repo} = 1 ]; then
    cd ${YANGDIR}
    git pull -q  >/dev/null 2>&1
    git submodule update -q --recursive --remote >/dev/null 2>&1
    if [ $? != 0 ]; then
        echo "WARNING: Failed to update YANG repo!"
    fi
fi

modules=""
update=0
first_run=1
find_args=""

while getopts ":f:" opt; do
  case $opt in
    f)
      if echo -- $OPTARG | grep -qE -- 'm$'; then
          find_args="-mmin $(echo $OPTARG | sed -E -e 's|m$||')"
      else
          find_args="-mtime $OPTARG"
      fi
      shift 2
      ;;
    \?)
      shift
      ;;
  esac
done

if [ $# = 0 ]; then
    modules=$(find ${TYANGDIR} -type f -name "*.yang" ${find_args})
else
    #cp -f ${DBF} ${TDBF}
    for m in $*; do
        if [ -d ${m} ]; then
            mods=$(find ${m} -type f -name "*.yang" ${find_args})
            modules="${modules} ${mods}"
            YANGREPO=${YANGREPO}:${m}
            DRAFTS_DIR="${DRAFTS_DIR} ${m}"
            RFCS_DIR="${RFCS_DIR} ${m}"
        else
            if echo ${m} | grep -qE '\.yang(:.+)?$'; then
                dname=$(dirname ${m})
                YANGREPO="${YANGREPO}:${dname}"
                modules="${modules} ${m}"
            fi
        fi
    done
    update=1
    first_run=0
fi

export YANGREPO
YANGREPO="$(perl -e 'print join(":", grep { not $seen{$_}++ } split(/:/, $ENV{YANGREPO}))')"

mtotal=$(echo ${modules} | wc -w)
mcur=0
cur_mod=""

trap -- 'update_progress ${mtotal} ${cur_mod} ${mcur}' 10 16 29 30

for mo in ${modules}; do
    mcur=$((${mcur} + 1))
    old_IFS=${IFS}
    IFS=":"
    mo_parts=(${mo})
    m=${mo_parts[0]}
    org=${mo_parts[1]}
    IFS=${old_IFS}
    cur_mod="${m}"
    cmd="pyang -p ${YANGREPO} -f yang-catalog-index --yang-index-make-module-table --yang-index-no-schema ${m}"
    if [ ${first_run} = 1 ]; then
        cmd="pyang -p ${YANGREPO} -f yang-catalog-index --yang-index-make-module-table ${m}"
        first_run=0
    fi
    mod_name_rev=$(pyang -p ${YANGREPO} -f name-revision ${m} 2>/dev/null | cut -d' ' -f1)
    old_IFS=${IFS}
    IFS="@"
    mod_parts=(${mod_name_rev})
    mod_name=${mod_parts[0]}
    mod_rev=${mod_parts[1]}
    IFS=${old_IFS}
    if [ ${update} = 1 ]; then
        echo "DELETE FROM modules WHERE module='${mod_name}' AND revision='${mod_rev}'; DELETE FROM yindex WHERE module='${mod_name}' AND revision='${mod_rev}';" | mysq
    else
        # Do not process duplicate modules
        output=$(echo "SELECT module FROM modules WHERE module='${mod_name}' AND revision='${mod_rev}';" | mysq)
        if [ $? = 0 -a -n "${output}" ]; then
            continue
        fi
    fi
    output=$(${cmd} 2> /dev/null)
#    echo "XXX: '${output}'"
    echo ${output} | mysq
    if [ $? != 0 ]; then
        echo "ERROR: Failed to update YANG DB for ${mod_name}@${mod_rev} (${m})!"
        continue
    fi

    echo "UPDATE modules SET file_path='${m}' WHERE module='${mod_name}' AND revision='${mod_rev}';" | mysq
    if [ $? != 0 ]; then
        echo "ERROR: Failed to update file path in YANG DB for ${mod_name}@${mod_rev} (${m})!"
    fi

    if [ -n "${org}" ]; then
      echo "UPDATE modules SET organization='${org}' WHERE module='${mod_name}' AND revision='${mod_rev}'; UPDATE yindex SET organization='${org}' WHERE module='${mod_name}' AND revision='${mod_rev}';" | mysq
      if [ $? != 0 ]; then
        echo "ERROR: Failed to update organization to ${org} in YANG DB for ${mod_name}@${mod_rev} (${m})!"
      fi
    fi

    # Generate YANG tree data.
    pyang -p ${YANGREPO} -f json-tree -o "${YTREE_DIR}/${mod_name}@${mod_rev}.json" ${m}
    if [ $? != 0 ]; then
        echo "WARNING: Failed to generate YANG tree data for ${mod_name}@${mod_rev} (${m})!"
    fi
    # XXX Hmmm, this is lame as symd only looks for mod name and not mod@rev
    #symd -r --rfc-repos ${RFCS_DIR} --draft-repos ${DRAFTS_DIR} --json-output ${YDEP_DIR}/${mod_name}.json --single-impact-analysis-json ${mod_name} 2>/dev/null
    #if [ $? != 0 ]; then
    #    echo "WARNING: Failed to generate YANG dependency data for ${mod_name} (${m})!"
    #fi

    if [ -n "${YANG_EXPLORER_DIR}" ]; then
      pyang -p ${YANGREPO} -f cxml ${m} > "${YANG_EXPLORER_DIR}/server/data/users/guest/cxml/${mod_name}@${mod_rev}.xml"
      if [ $? != 0 ]; then
        echo "WARNING: Failed to generate YANG Explorer data for ${mod_name} (${m})!"
      else
        cp -f ${m} "${YANG_EXPLORER_DIR}/server/data/users/guest/yang/${mod_name}@${mod_rev}.yang"
      fi
    fi
done

for cf in ${YANG_CATALOG_FILES}; do
  ${TOOLS_DIR}/process-catalog-file.py ${cf} ${DBNAME} ${YDEP_DIR} ${HOST} ${USER} ${PASSWD}
  if [ $? != 0 ]; then
    echo "WARNING: Failed to process YANG catalog file for ${cf}!"
  fi
done

${TOOLS_DIR}/add-catalog-data.py ${DBNAME} ${HOST} ${USER} ${PASSWD}
if [ $? != 0 ]; then
    echo "WARNING: Failed to add YANG catalog data!"
fi

if [ -n "${YANG_EXPLORER_DIR}" ]; then
    cd ${YANG_EXPLORER_DIR}
    ./reload.sh
fi
#
#mv -f ${TDBF} ${DBF}
#chmod 0644 ${DBF}

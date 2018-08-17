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

function cleanup() {
    rm -f ${YANGDIR}/YANG-drafts.tar ${YANGDIR}/YANG-RFC.tar
    rm -rf ${YANGDIR}/tmp
}

if [ -z "${YANG_INDEX_HOME}" ]; then
    echo "ERROR: YANG_INDEX_HOME environment variable not defined; please set this to the path to the yindex.env file"
    exit 1
fi

. ${YANG_INDEX_HOME}/yindex.env

cd ${YANGDIR}
LATEST_DIR=${YANGDIR}/standard/ietf/latest

cleanup
mkdir -p tmp/DRAFT
mkdir -p tmp/RFC

curl -LO http://www.claise.be/YANG-drafts.tar
if [ $? != 0 ]; then
    echo "ERROR: Failed to download drafts tarball"
    exit 1
fi

curl -LO http://www.claise.be/YANG-RFC.tar
if [ $? != 0 ]; then
    echo "ERROR: Failed to download RFC tarball"
    exit 1
fi

cd tmp/DRAFT
tar -xf ${YANGDIR}/YANG-drafts.tar
if [ $? != 0 ]; then
    echo "ERROR: Failed to extract draft tarball"
    exit 1
fi

cd ${YANGDIR}/tmp/RFC
tar -xf ${YANGDIR}/YANG-RFC.tar
if [ $? != 0 ]; then
    echo "ERROR: Failed to extract RFC tarball"
    exit 1
fi

rm -rf ${LATEST_DIR}
mkdir -p ${LATEST_DIR}
mv -f ${YANGDIR}/tmp/DRAFT ${LATEST_DIR}
mv -f ${YANGDIR}/tmp/RFC ${LATEST_DIR}

cd ${YANGDIR}
export DRAFTS_DIR=${LATEST_DIR}/DRAFT
export RFCS_DIR=${LATEST_DIR}/RFC
export YANGREPO=${LATEST_DIR}

${TOOLS_DIR}/build_yindex.sh ${LATEST_DIR}
cleanup

# Copyright The IETF Trust 2019, All Rights Reserved
# Copyright 2018 Cisco and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
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

"""Name@revision output plugin

"""

from pyang import plugin


def pyang_plugin_init():
    plugin.register_plugin(NameRevisionPlugin())


class NameRevisionPlugin(plugin.PyangPlugin):

    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['name-revision'] = self

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        emit_name(ctx, modules, fd)


def emit_name(ctx, modules, fd):
    for module in modules:
        bstr = ""
        rstr = ""
        b = module.search_one('belongs-to')
        r = module.search_one('revision')
        if b is not None:
            bstr = " (belongs-to %s)" % b.arg
        if r is not None:
            rstr = '@%s' % r.arg
        fd.write("%s%s%s\n" % (module.arg, rstr, bstr))

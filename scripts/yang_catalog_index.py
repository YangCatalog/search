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

from pyang import plugin, statements
import json
import optparse
import re

_yang_catalog_index_fd = None
_yang_catalog_index_values = []

NS_MAP = {
    "http://cisco.com/ns/yang/": "cisco",
    "http://www.huawei.com/netconf": "huawei",
    "http://openconfig.net/yang": "openconfig",
    "http://tail-f.com/": "tail-f"
}


def pyang_plugin_init():
    plugin.register_plugin(IndexerPlugin())


class IndexerPlugin(plugin.PyangPlugin):

    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts['yang-catalog-index'] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option("--yang-index-no-schema",
                                 dest="yang_index_no_schema",
                                 action="store_true",
                                 help="""Do not include SQL schema in output"""),
            optparse.make_option("--yang-index-schema-only",
                                 dest="yang_index_schema_only",
                                 action="store_true",
                                 help="""Only include the SQL schema in output"""),
            optparse.make_option("--yang-index-make-module-table",
                                 dest="yang_index_make_module_table",
                                 action="store_true",
                                 help="""Generate a modules table that includes various aspects about the modules themselves""")
        ]

        g = optparser.add_option_group("YANG Catalog Index specific options")
        g.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        global _yang_catalog_index_fd

        _yang_catalog_index_fd = fd
        emit_index(ctx, modules, fd)


def emit_index(ctx, modules, fd):
    global  _yang_catalog_index_values
    if not ctx.opts.yang_index_no_schema:
        fd.write(
            "CREATE TABLE yindex(module, revision, organization, path, statement, argument, description, properties);\n")
        if ctx.opts.yang_index_make_module_table:
            fd.write(
                "CREATE TABLE modules(module, revision, yang_version, belongs_to, namespace, prefix, organization, maturity, compile_status, document, file_path);\n")
    if not ctx.opts.yang_index_schema_only:
        _yang_catalog_index_values = [] ;
        mods = []
        for module in modules:
            if module in mods:
                continue
            mods.append(module)
            for i in module.search('include'):
                subm = ctx.get_module(i.arg)
                if subm is None:
                    r = module.search_one('revision')
                    if r is not None:
                        subm = ctx.search_module(module.pos, i.arg, r.arg)
                if subm is not None:
                    mods.append(subm)
        for module in mods:
            if ctx.opts.yang_index_make_module_table:
                index_mprinter(ctx, module)
            non_chs = list(module.i_typedefs.values()) + list(module.i_features.values()) + list(module.i_identities.values()) + \
                list(module.i_groupings.values()) + list(module.i_extensions.values())
            for augment in module.search('augment'):
                if (hasattr(augment.i_target_node, 'i_module') and
                        augment.i_target_node.i_module not in mods):
                    for child in augment.i_children:
                        statements.iterate_i_children(child, index_printer)
            for nch in non_chs:
                index_printer(nch)
            for child in module.i_children:
                statements.iterate_i_children(child, index_printer)
        if len(_yang_catalog_index_values) > 0:
            _yang_catalog_index_fd.write("INSERT INTO yindex (module, revision, organization, path, statement, argument, description, properties) VALUES " + ', '.join(_yang_catalog_index_values) + ';\n')


def index_mprinter(ctx, module):
    global _yang_catalog_index_fd

    params = [module.arg]
    args = ['revision', 'yang-version', 'belongs-to',
            'namespace', 'prefix', 'organization']
    # Allow for changes to the params array wihtout needing to remember to
    # adjust static index numbers.
    bt_idx = args.index('belongs-to') + 1
    ns_idx = args.index('namespace') + 1
    org_idx = args.index('organization') + 1
    rev_idx = args.index('revision') + 1
    prefix_idx = args.index('prefix') + 1
    ver_idx = args.index('yang-version') + 1
    for a in args:
        nlist = module.search(a)
        nstr = ''
        if nlist:
            nstr = nlist[0].arg
            # Need to escape the single quote as it will be inserted in SQL
            nstr = nstr.replace("'", r"''")
            params.append(nstr)
        else:
            params.append('')
    # Attempt to normalize the organization for catalog retrieval.
    if params[bt_idx] is not None and params[bt_idx] != '':
        (res_ns, res_pf) = get_namespace_prefix(ctx, module)
        params[ns_idx] = res_ns
        params[prefix_idx] = res_pf
    params[org_idx] = normalize_org(params[org_idx], params[ns_idx])

    if params[ver_idx] is None or params[ver_idx] == '' or params[ver_idx] == '1':
        params[ver_idx] = '1.0'
    if params[rev_idx] == '':
        params[rev_idx] = '1970-01-01'
    # We don't yet know the maturity of the module, but we can get that from
    # the catalog later.
    # The DB columns below need to be in the same order as the args list above.
    _yang_catalog_index_fd.write(
        "INSERT INTO modules (module, revision, yang_version, belongs_to, namespace, prefix, organization) VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s');" % tuple(params) + "\n")


def get_namespace_prefix(ctx, module):
    prefix = ''
    namespace = ''
    revision = None

    bt = module.search_one('belongs-to')
    pf = bt.search_one('prefix')
    rev = bt.search_one('revision')
    if pf is not None:
        prefix = pf.arg
    if rev is not None:
        revision = rev.arg
    pm = ctx.get_module(bt.arg, revision)
    if pm is None:
        pm = ctx.search_module(module.pos, bt.arg, revision)
    if pm is not None:
        ns = pm.search_one('namespace')
        if ns is not None:
            namespace = ns.arg

    return (namespace, prefix)


def normalize_org(o, ns):
    m = re.search(r'urn:([^:]+):', ns)
    if m:
        return m.group(1)

    for n, org in NS_MAP.items():
        if re.search(r'^' + n, ns):
            return org

    if o == '':
        return 'independent'

    return o


def index_escape_json(s):
    return s.replace("\\", r"\\").replace("'", r"''").replace("\n", r"\n").replace("\t", r"\t").replace("\"", r"\"")


def flatten_keyword(k):
    if type(k) is tuple:
        k = ':'.join(map(str, k))

    return k


def index_get_other(stmt):
    a = stmt.arg
    k = flatten_keyword(stmt.keyword)
    if a:
        a = index_escape_json(a)
    else:
        a = ''
    child = {k: {'value': a, 'has_children': False}}
    child[k]['children'] = []
    for ss in stmt.substmts:
        child[k]['has_children'] = True
        child[k]['children'].append(index_get_other(ss))
    return child


def index_printer(stmt):
    global _yang_catalog_index_values

    if stmt.arg is None:
        return

    skey = flatten_keyword(stmt.keyword)

    module = stmt.i_module
    rev = module.search_one('revision')
    org = module.search_one('organization')
    ns = module.search_one('namespace')
    revision = ''
    organization = ''
    namespace = ''
    if rev:
        revision = rev.arg
    if ns:
        namespace = ns.arg
    if namespace == '':
        (namespace, res_pf) = get_namespace_prefix(
            module.i_ctx, module)
    if org:
        organization = org.arg
    organization = normalize_org(organization, namespace)
    # Need to escape the single quote for SQL
    organization = organization.replace("'", "''")
    path = statements.mk_path_str(stmt, True)
    descr = stmt.search_one('description')
    dstr = ''
    if descr:
        dstr = descr.arg
        dstr = dstr.replace("'", "''")
    subs = []
    if revision == '':
        revision = '1970-01-01'
    for i in stmt.substmts:
        a = i.arg
        k = i.keyword

        k = flatten_keyword(k)

        if i.keyword not in statements.data_definition_keywords:
            subs.append(index_get_other(i))
        else:
            has_children = hasattr(i, 'i_children') and len(i.i_children) > 0
            if not a:
                a = ''
            else:
                a = index_escape_json(a)
            subs.append(
                {k: {'value': a, 'has_children': has_children, 'children': []}})
    sql_value = "('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (module.arg, revision, organization, path, skey, stmt.arg, dstr, json.dumps(subs))
    if len(_yang_catalog_index_values) > 100:
        _yang_catalog_index_fd.write("INSERT INTO yindex (module, revision, organization, path, statement, argument, description, properties) VALUES " + ', '.join(_yang_catalog_index_values) + ';\n')
        _yang_catalog_index_values = []
    _yang_catalog_index_values.append(sql_value)

from django.shortcuts import render
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.shortcuts import redirect
from Crypto.Hash import SHA, HMAC
import configparser
import math
import requests
import logging
import json
import os
import time

from .models import modules
from .models import yindex

__module = [
    'name', 'revision', 'organization', 'ietf', 'namespace', 'schema', 'generated-from', 'maturity-level',
    'document-name', 'author-email', 'reference', 'module-classification', 'compilation-status',
    'compilation-result', 'prefix', 'yang-version', 'description', 'contact', 'module-type', 'belongs-to',
    'tree-type', 'yang-tree', 'expires', 'expired', 'submodule', 'dependencies', 'dependents',
    'semantic-version', 'derived-semantic-version', 'implementations'
]

search_fields = {'Module Name': 'module', 'Node Name': 'argument', 'Node Description': 'description'}
yang_versions = ['1.0', '1.1']
schema_types = [{'Typedef': 'typedef', 'Grouping': 'grouping', 'Feature': 'feature'},
                {'Identity': 'identity', 'Extension': 'extension', 'RPC': 'rpc'},
                {'Container': 'container', 'List': 'list', 'Leaf-List': 'leaf-list'},
                {'Leaf': 'leaf', 'Notification': 'notification', 'Action': 'action'}]

CHANGES_CACHE = '/usr/share/nginx/yang2_repo_cache.dat'
DELETE_CACHE = '/usr/share/nginx/yang2_repo_deletes.dat'
REST_TIMEOUT = 300
LOCKF = '/tmp/webhook.lock'

alerts = []
MATURITY_UNKNOWN = '#663300'
MATURITY_MAP = {
    'INITIAL': '#c900ff',
    'ADOPTED': '#86b342',
    'RATIFIED': '#0066ff',
    'N/A': '#663300',
    'COMPILATION FAILED': '#ff0000',
}

ORG_CACHE = dict()
NUM_STEPS = -1
CUR_STEP = 1
seen_modules = dict()

SDOS = [
    'ietf',
    'ieee',
    'bbf',
    'odp',
]

found_orgs = dict()
found_mats = dict()

logger = logging.getLogger(__name__)


def index(request):
    """ View for default search page. Takes arguments from search request,
    and send them to function search().
    :return context for index.html for displaying search results
    """
    search_term = ''
    search_columns = [
        "Name",
        "Revision",
        "Schema Type",
        "Path",
        "Module",
        "Origin",
        "Organization",
        "Maturity",
        "Imported By # Modules",
        "Compilation Status",
        "Description"
    ]
    post_json = {
        'filter': {
            'module': [
                'name',
                'revision',
                'organization',
                'maturity-level',
                'compilation-status',
                'dependents'
            ]
        }
    }
    if 'search_string' in request.GET:
        search_term = request.GET['search_string']
        post_json['search'] = search_term

    if 'case' in request.GET:
        post_json['case-sensitive'] = True
    else:
        post_json['case_sensitive'] = False

    if 'regexp' in request.GET:
        post_json['type'] = 'regex'
    else:
        post_json['type'] = 'keyword'

    if 'includeMIBs' in request.GET:
        post_json['include-mibs'] = True
    else:
        post_json['include-mibs'] = False

    if 'onlyLatest' in request.GET:
        post_json['latest-revisions'] = True
    else:
        post_json['latest-revisions'] = False

    if 'fieldsAll' in request.GET:
        post_json['search-fields'] = ['module', 'argument', 'description']
    elif 'searchFields[]' in request.GET:
        post_json['search-fields'] = []
        fields = request.GET.getlist('searchFields[]')
        for field in fields:
            post_json['search-fields'].append(field)

    if 'yangVersions[]' in request.GET:
        versions = request.GET.getlist('yangVersions[]')
        post_json['yang-versions'] = []
        for version in versions:
            post_json['yang-versions'].append(version)

    if 'schemaAll' not in request.GET:
        if 'schemaTypes[]' in request.GET:
            types = request.GET.getlist('schemaTypes[]')
            post_json['schema-types'] = []
            for one_type in types:
                post_json['schema-types'].append(one_type)

    output = search(post_json, search_term)
    context = dict()

    new_columns = json.dumps(search_columns)

    context.update({'search_term': search_term, 'search_fields': search_fields,
                    'yang_versions': yang_versions, 'schema_types': schema_types, 'alerts': alerts,
                    'search_columns': search_columns, 'new_columns': new_columns})
    context['results'] = output
    return render(request, 'search/index.html', context)


def show_node(request, name='', path='', revision=''):
    """
    View for show_node page, which provides context for show_node.html
    Shows description for yang modules.
    :param request: Array with arguments from webpage data submition.
    :param module: Takes first argument from url if request does not
    contain module argument.
    :param path: Path for node.
    :param revision: revision for yang module, if specified.
    :return: returns context for show_node.html 
    """
    alerts = []
    context = dict()
    try:
        if not revision:
            revision = get_latest_mod(name, alerts)
            revision = revision.split('@')[1]
        node = yindex.objects.filter(module=name, path=path, revision=revision)[:1]
        if node is None:
            alerts.append('Could not find data for {} at {}'.format(name, path))
        result = node.values().get()
        context['show_node'] = result
        context['properties'] = json.loads(result['properties'])
    except:
        alerts.append('Module and path must be specified')
    context['alerts'] = alerts 
    return render(request, 'search/show_node.html', context)


def module_details(request, module=''):
    """
    View for module_details, which provides context for module_details.html
    Takes request args, and makes requests to local database, and api.
    :param request: Array with arguments from webpage data submition.
    :param module: Takes first argument from url if request does not
    contain module argument.
    :return: returns context for module_details.html
    """
    alerts = []
    context = dict()
    if 'module' in request.GET:
        module = request.GET['module']
    title = 'Module Details'
    try:
        if 'module' in request.GET:
            module = request.GET['module']
        module = module.replace('.yang', '')
        module = module.replace('.yin', '')
        rev_org = get_rev_org('yang-catalog', 1, alerts)
        revision = rev_org['rev']
        
        mod = yindex.objects.values('argument', 'description', 'properties') \
            .filter(module='yang-catalog', revision=revision) \
            .order_by('argument', 'module', 'revision')
        
        rv_org = get_rev_org(module, 1, alerts)
        module = module.split('@')[0]
        rv = rv_org['rev']
        org = rv_org['org']
        url = 'https://yangcatalog.org/api/search/modules/' + module + ',' + rv + ',' + org
        response = requests.get(url, headers={'Content-type': 'application/json', 'Accept': 'application/json'})
        if response.text is not None:
            results = json.loads(response.text)['module']
        else:
            alerts.append('Module not Found.')
        module_details = dict()
        for key in __module:
            help_text = ''
            val = ''
            for result in results:
                if result.get(key) is not None:
                    module_details[key] = result.get(key)
                else:
                    module_details[key] = ''
            for m in mod:
                if m.get('argument') is not None and m.get('argument') == key:
                    if m.get('description') is not None:
                        help_text = m.get('description')
                    nprops = json.loads(m['properties'])
                    for prop in nprops:
                        if prop.get('type') is not None:
                            if prop.get('type')['has_children'] == True:
                                for child in prop['type']['children']:
                                    if child.get('enum') and child['enum']['has_children'] == True:
                                        for echild in child['enum']['children']:
                                            if echild.get('description') is not None:
                                                description = echild['description']['value'].replace('\n', "<br/>\r\n")
                                                help_text += "<br/>\r\n<br/>\r\n{} : {}".format(child['enum']['value'],
                                                                                                description)
    
                        break
                module_details['{}_ht'.format(key)] = help_text
    
        context['module_details'] = module_details
        context['keys'] = __module
        context['module'] = module
        context['revision'] = rv
        context['organization'] = org
        context['title'] = 'Module Details for {}@{}/{}'.format(module, rv, org)
    except Exception as e:
        context['title'] = title
        return render(request, 'search/module_details.html', context)
    return render(request, 'search/module_details.html', context)


def completions(request, type, pattern):
    """
    Provides auto-completions for search bars on web pages impact_analysis
    and module_details.
    :param request: Array with arguments from webpage data submition.
    :param type: Type of what we are auto-completing, module or org.
    :param pattern: Pattern which we are writing in bar.
    :return: auto-completion results
    """
    alerts = []
    string = ''
    if len(alerts) != 0:
        pass
    res = []

    if type is None or (type != 'org' and type != 'module'):
        string += json.dumps(res, cls=DjangoJSONEncoder)
        return HttpResponse(string)

    if not pattern:
        string += json.dumps(res, cls=DjangoJSONEncoder)
        return HttpResponse(string)

    selector = None
    try:
        if type == 'org':
            selector = 'organization'
            rows = modules.objects.values('organization').filter(organization__contains=pattern).distinct()[:10]
            for row in rows:
                res.append(row[selector])
        elif type == 'module':
            selector = 'module'
            rows = modules.objects.values('module').filter(module__contains=pattern).distinct()[:10]
            for row in rows:
                res.append(row[selector])

    except Exception as e:
        raise Exception(e)
    return HttpResponse(json.dumps(res, cls=DjangoJSONEncoder), content_type="application/json")


def create_signature(secret_key, string):
    """ Create the signed message from api_key and string_to_sign
    Arguments:
    :param string: (str) String that needs to be signed
    :param secret_key: Secret key that the string will be signed with
    :return A string of 2* `digest_size` bytes. It contains only
    hexadecimal ASCII digits.
    """
    string_to_sign = string.encode('utf-8')
    string_to_sign = b'\n' + string_to_sign
    hmac = HMAC.new(secret_key.encode('utf-8'), string_to_sign, SHA)
    return hmac.hexdigest()


def yangsuite(request, module):
    """
    Generates link for yangsuite for module.
    :param request: Array with arguments from webpage data submition.
    :param module: module for which we are generating url.
    :return: url
    """
    alerts = []
    url = ''
    if module is None:
        alerts.append("ERROR: You must specify a module.")
    else:
        module = module.replace('.yang', '')
        module = module.replace('.yin', '')
        rev_org = get_rev_org(module, 1, alerts)
        module = module.split('@')[0]
        mod_obj = moduleFactory(module, rev_org['rev'], rev_org['org'], False, True)
        obj = fetch(mod_obj)
            
        if obj.get('ys_url') is not None:
            url = obj['ys_url']

        return redirect(url)


def fetch(mod_obj):
    """
    Takes module object and requests additional arguments from api and database
    to complete all information necessary about the module.
    :param mod_obj: module object
    :return: module with all arguments
    """
    url = 'https://yangcatalog.org/api/search/modules/' + mod_obj['name'] + ',' + mod_obj['revision'] + ',' + mod_obj[
        'organization']
    if mod_obj.get('yang_suite'):
        response = requests.get(url, headers={'Content-type': 'application/json', 'Accept': 'application/json',
                                              'yangsuite': 'true', 'yang_set': mod_obj['name']})
    else:
        response = requests.get(url, headers={'Content-type': 'application/json', 'Accept': 'application/json'})
    results = json.loads(response.text)
    for result in results['module']:
        for key, value in result.items():
            # if key in __module:
            mod_obj[key] = value
        if mod_obj.get('yang_suite') and results.get('yangsuite-url') is not None:
            mod_obj['ys_url'] = results.get('yangsuite-url')
    return mod_obj


# @csrf_protect
def metadata_update(request):
    """
    Provides hyperlink for database update, on which we send requests.
    :param request: Array with arguments from rest request.
    :return: calls scripts for database update and file generation 
    """
    config = configparser.ConfigParser()
    config.read('/home/tomas/yang_search/yang/config.ini')
    update_signature = config.get('DB-Section', 'update_signature')
    lock_count = 0
    body_unicode = request.body.decode('utf-8')
    signature = create_signature(update_signature, body_unicode)
    while os.path.exists(LOCKF):
        if lock_count > 20:
            return HttpResponse(status=500)
        time.sleep(3)
        lock_count += 1
    try:
        res = os.utime(LOCKF, None)
        if not res:
            raise Exception('Failed to obtain lock ' + LOCKF)

        if request.META.get('REQUEST_METHOD') is None or request.META['REQUEST_METHOD'] != 'POST':
            raise Exception('Invalid request method')
        if request.META.get('HTTP_X_YC_SIGNATURE') is None or request.META[
            'HTTP_X_YC_SIGNATURE'] != 'sha1=' + signature:
            raise Exception('Invalid message signature')

        changes_cache = dict()
        delete_cache = dict()
        if os.path.exists(CHANGES_CACHE) and os.path.getsize(CHANGES_CACHE) > 0:
            changes_cache = json.loads(open(CHANGES_CACHE))
        if os.path.exists(DELETE_CACHE) and os.path.getsize(DELETE_CACHE) > 0:
            delete_cache = json.loads(open(DELETE_CACHE))

        js = json.loads(body_unicode)
        if js.get(['modules-to-index']) is None:
            js['modules-to-index'] = []

        if js.get(['modules-to-delete']) is None:
            js['modules-to-delete'] = []

        for mname, mpath in js['modules-to-index']:
            changes_cache[mname] = mpath
        for mname in js['modules-to-delete']:
            if [k for k, v in delete_cache.items() if v == mname][0]:
                delete_cache.append(mname)
        fd = open(CHANGES_CACHE, 'w')
        fd.write(json.dumps(changes_cache))
        fd.close()
        fd = open(DELETE_CACHE, 'w')
        fd.write(json.dumps(delete_cache))
        fd.close()
    except Exception as e:
        raise Exception("Caught exception {}".format(e))
    os.unlink(LOCKF)


def yang_tree(request, module = ''):
    """
    View for yang_tree.html webpage. Generates yang tree view of the module.
    :param request: Array with arguments from rest request.
    :param module: Module for which we are generating the tree.
    :return: Context for yang_tree.html
    """
    context = dict()
    alerts = []
    jstree_json = None
    json_tree = dict()
    modn = ''
    title = ''
    maturity = ''
    if module == '':
        alerts.append('Module was not specified')
    else:
        nmodule = os.path.basename(module)
        if nmodule != module:
            alerts.append('Invalid module name specified')
            module = ''
        else:
            title = "YANG Tree for Module: '{}'".format(module)
            mod_obj = get_rev_org(module, 1, alerts)

            modn = module.split('@', 1)[0]
            module = "{}@{}".format(modn, mod_obj['rev'])
            f = '/var/yang/ytrees/{}.json'.format(module)
            maturity = get_maturity(mod_obj)
            if os.path.isfile(f):
                try:
                    contents = open(f).read()
                    json_tree = json.loads(contents)
                    if json_tree.get('namespace') is None:
                        json_tree['namespace'] = ''
                    if json_tree is None:
                        alerts.append('Failed to decode JSON data: ')
                    else:
                        data_nodes = build_tree(json_tree, modn)
                        jstree_json = dict()
                        jstree_json['data'] = [data_nodes]
                        if json_tree.get('rpcs') is not None:
                            rpcs = dict()
                            rpcs['name'] = json_tree['prefix'] + ':rpcs'
                            rpcs['children'] = json_tree['rpcs']
                            jstree_json['data'].append(build_tree(rpcs, modn))
                        if json_tree.get('notifications') is not None:
                            notifs = dict()
                            notifs['name'] = json_tree['prefix'] + ':notifs'
                            notifs['children'] = json_tree['notifications']
                            jstree_json['data'].append(build_tree(notifs, modn))
                        if json_tree.get('augments') is not None:
                            augments = dict()
                            augments['name'] = json_tree['prefix'] + ':augments'
                            augments['children'] = json_tree['augments']
                            jstree_json['data'].append(build_tree(augments, modn))
                except Exception as e:
                    alerts.append("Failed to read YANG tree data for {}, {}".format(module, e))
            else:
                alerts.append("YANG Tree data does not exist for {}".format(module))
    if jstree_json is not None:
        context['jstree_json'] = json.dumps(jstree_json, cls=DjangoJSONEncoder)
    context['module'] = module
    if modn:
        context['modn'] = modn
    else:
        context['modn'] = module
    context['alerts'] = alerts
    if json_tree:
        context['json_tree'] = json_tree
    context['title'] = title
    context['maturity'] = maturity
    return render(request, 'search/yang_tree.html', context)


def impact_analysis(request, module=''):
    """
    View for impact_analysis.html 
    :param request: Array with arguments from rest request.
    :param module: Module for which we are generating impact_analysis, this arg is only used
    when we are accessing webpage from link in search. Otherwise request arguments are used.
    :return: Context for generating the impact_analysis webpage.
    """
    context = dict()
    DIR_HELP_TEXT = "<b>Both:</b> Show a graph that consists of both dependencies (modules imported by the target module(s)) and dependents (modules that import the target module(s))<br/>&nbsp;<br/>\n" \
                    + "<b>Dependencies Only:</b> Only show those modules that are imported by the target module(s)<br/>&nbsp;<br/>\n" \
                    + '<b>Dependents Only:</b> Only show those modules that depend on the target module(s)'
    alerts = []
    title = 'Empty Impact Graph'
    context['title'] = title
    try:
        nodes = []
        edges = []
        edge_counts = dict()
        nseen = dict()
        eseen = dict()
        mods = []
        good_mods = []
        show_rfcs = True
        recurse = 0
        show_subm = True
        show_dir = 'both'
        found_bottleneck = False
        bottlenecks = []
        global found_orgs, found_mats
        num_legend_cols = 1
        rim_cols = 0
        if 'modtags' in request.GET:
            mods = request.GET['modtags'].split(',')
        else:
            if module:
                mods.append(module)
        if 'orgtags' in request.GET and request.GET['orgtags'] != '':
            orgs = request.GET['orgtags'].split(',')
        else:
            orgs = []
        if 'recursion' in request.GET:
            try:
                recurse = int(request.GET['recursion'])
            except:
                recurse = 0
                
        if 'show_rfcs' not in request.GET and request.GET != {}:
            show_rfcs = False
        if 'show_subm' not in request.GET and request.GET != {}:
            show_subm = False
        if 'show_dir' in request.GET:
            show_dir = request.GET['show_dir']
            if show_dir != 'both' and show_dir != 'dependencies' and show_dir != 'dependents':
                show_dir = 'both'
        if 'ietf_wg' in request.GET:
            ietf_wg = request.GET['ietf_wg']
            mod_objs = moduleFactoryFromSearch("ietf/ietf-wg/{}".format(ietf_wg))
            if not mod_objs or len(mod_objs) == 0:
                alerts.append("No modules found for {}".format(ietf_wg))
            else:
                for mod_obj in mod_objs:
                    if mod_obj.get('name') is not None:
                        m = mod_obj['name']
                        
                        if mod_obj.get('maturity-level') != 'adopted' and mod_obj.get('maturity-level') != 'ratified':
                            continue
                        good_mods.append(m)
                        mods.append(m)
                        build_graph(m, mod_obj, orgs, nodes, edges, edge_counts, nseen, eseen, alerts, show_rfcs,
                                    recurse, False, show_subm, show_dir)
        else:
            for m in mods:
                nmodule = os.path.basename(m)
                if nmodule != m:
                    alerts.append('Invalid module name specified')
                    m = ''
                else:
                    m = m.replace('.yang', '')
                    m = m.replace('.yin', '')
                    mod_obj = get_rev_org_obj(m, alerts)
                    m = m.split('@')[0]
                    good_mods.append(m)
                    build_graph(m, mod_obj, orgs, nodes, edges, edge_counts, nseen, eseen, alerts, show_rfcs,
                                recurse, False, show_subm, show_dir)
        if len(good_mods) > 0:
            title = 'YANG Impact Graph for Module(s): ' + ', '.join(good_mods)
        edge_counts = asort(edge_counts)
        curr_count = 0
        tbottlenecks = []
        rim_cols = len(found_mats)
        for pair in edge_counts:
            if pair[1] < 1 or pair[1] < curr_count:
                break
            tbottlenecks.append(pair[0])
            found_bottleneck = True
            curr_count = pair[1]
    
        for bn in tbottlenecks:
            found_dep = False
            for edge in edges:
                if edge['data']['target'] == "mod_{}".format(bn):
                    mn = edge['data']['source'].replace('mod_', '')
                    mo = get_rev_org_obj(mn, alerts)
                    maturity = get_maturity(mo)
                    if maturity['level'] == 'INITIAL' or maturity['level'] == 'ADOPTED':
                        bottlenecks.append("node#{}".format(edge['data']['source']))
                        found_dep = True
            if not found_dep:
                bottlenecks.append("node#mod_{}".format(bn))
    
        num_legend_cols = math.ceil(len(found_orgs) / 6)
        if num_legend_cols < 1:
            num_legend_cols = 1
        if found_bottleneck:
            rim_cols += 1
        if rim_cols > 1:
            rim_cols -= 1
        context['alerts'] = alerts
        context['nodes'] = nodes
        context['nodes_json'] = json.dumps(nodes, cls=DjangoJSONEncoder)
        context['edges'] = edges
        context['edges_json'] = json.dumps(edges, cls=DjangoJSONEncoder)
        context['edge_counts'] = edge_counts
        context['nseen'] = nseen
        context['eseen'] = eseen
        context['modules'] = mods
        context['good_mods'] = good_mods
        context['orgs'] = orgs
        context['show_rfcs'] = show_rfcs
        context['recurse'] = recurse
        context['show_subm'] = show_subm
        context['show_dir'] = show_dir
        context['found_bottleneck'] = found_bottleneck
        context['bottlenecks'] = bottlenecks
        context['title'] = title
        context['num_legend_cols'] = num_legend_cols
        context['rim_cols'] = rim_cols
        context['MATURITY_MAP'] = MATURITY_MAP
        context['found_orgs'] = found_orgs
        found_orgs = {}
        context['ORG_CACHE'] = ORG_CACHE
        context['found_mats'] = found_mats
        found_mats = {}
        context['DIR_HELP_TEXT'] = DIR_HELP_TEXT
    except Exception as e:
        context['alerts'] = alerts
        logger.error(e)
        return render(request, 'search/impact_analysis.html', context)
    return render(request, 'search/impact_analysis.html', context)


def search(post_json, search_term):
    """
    Searches for results of the main yang-search webpage.
    :param post_json: Json which we are sending to api
    :param search_term: Term for which we are searching
    :return: Search results. 
    """
    if search_term != '':

        response = requests.post('https://yangcatalog.org/api/index/search', json=post_json,
                                 headers={'Content-type': 'application/json', 'Accept': 'application/json'})
        results = response.json().get('results')

        all_results = []

        if results is None:
            return ''
        for result in results:

            results_context = {}
            module = result.get('module')
            node = result.get('node')

            type = ''
            path = ''
            node_name = ''
            description = ''

            if module is not None:
                if module.get('error') is not None:
                    return alerts.append(module.get('error'))
                if module['name'] is None:
                    continue
                organization = module['organization']
                if module.get('maturity-level') is not None:
                    maturity = module.get('maturity-level')
                else:
                    maturity = ''
                revision = module['revision']
                dependents = module['dependents']
                if dependents:
                    dependents = len(dependents)
                else:
                    dependents = '0'
                compile_status = module['compilation-status']
                mod_sig = "{}@{}/{}".format(
                    module['name'], module['revision'], module['organization']
                )
                name = module['name']
            else:
                continue

            if organization is None or organization == '':
                organization = 'N/A'

            origin = 'N/A'
            if organization != 'N/A' and organization in SDOS:
                origin = 'Industry Standard'
            elif organization != 'N/A':
                origin = 'Vendor-Specific'

            if node is not None:
                type = node['type']
                path = node['path']
                node_name = node['name']
                description = node['description']

            results_context["name"] = name
            results_context["organization"] = organization
            results_context["maturity"] = maturity
            results_context["compile_status"] = compile_status
            results_context["origin"] = origin
            results_context["mod_sig"] = mod_sig
            results_context["revision"] = revision
            results_context["type"] = type
            results_context["path"] = path
            results_context["dependents"] = dependents
            results_context["node_name"] = node_name
            results_context["description"] = description
            all_results.append(results_context)
        return all_results
    else:
        return ''


def get_rev_org(mod, depth=1, alerts=[]):
    """
    Gets revision and organization for specified Module.
    :param mod: Module name
    :param depth: Searches dependents for module to get newest rev and org
    :return: revision and organization
    """
    try:
        if '@' in mod:
            mod_parts = mod.split('@')
            modn = mod_parts[0]
            rev = mod_parts[1]
            rev_org = modules.objects.values('revision', 'organization').filter(module=modn, revision=rev)
        else:
            rev_org = modules.objects.filter(module=mod).values('revision', 'organization') \
                          .order_by('-revision')[:depth]
        row = dict()
        i = 1
        for result in rev_org:
            if i > depth:
                break
            row.update(result)
            i += 1
        if not row.get('organization'):
            row['organization'] = 'independent'
        if row.get('revision') is not None:
            return {'org': row['organization'], 'rev': row['revision']}
        else:
            return {'org': row['organization'], 'rev': ''}
    except Exception as e:
        alerts.append("Failed to get module revision and organization for {}, {}".format(mod, e))


def get_rev_org_obj(module, alerts):
    """
    Gets revision and organization but also fills other arguments of module object.
    :param module: module name
    :return: module
    """
    depth = 1
    while True:
        rev_org = get_rev_org(module, depth, alerts)
        modn = module.split('@')[0]
        if rev_org.get('rev') is None or rev_org.get('rev') == '':
            alerts.append("Failed to find revision for module {} in the API".format(module))
            return
        mobj = moduleFactory(modn, rev_org['rev'], rev_org['org'])
        try:
            url = 'https://yangcatalog.org/api/search/modules/' + modn + ',' + rev_org['rev'] + ',' + rev_org['org']
            response = requests.get(url, headers={'Content-type': 'application/json', 'Accept': 'application/json'})
            results = json.loads(response.text).get('module')
            if results is not None:
                for result in results:
                    for k, v in result.items():
                        if k in __module:
                            mobj[k] = v
            else:
                return dict()
            return mobj
        except Exception as e:
            logger.error(e)
            depth += 1


def moduleFactory(name, revision, organization, override=False, yang_suite=False, attrs=dict()):
    """
    Checks whether module isn't already filled, and creates it if not.
    :param name: module name
    :param revision: revision of module
    :param organization: author organization
    :param override: if enabled, recreates module from scratch
    :param yang_suite: tells whether to request yangsuite url as well.
    :param attrs: attributes which are already avaiable
    :return: module
    """
    mod_sig = "{}@{}/{}".format(name, revision, organization)
    create_new = False
    if yang_suite:
        create_new = True
    if seen_modules.get(mod_sig) is None:
        create_new = True
    elif override:
        seen_modules[mod_sig] = None
        create_new = True
    if create_new:
        seen_modules[mod_sig] = constructModule(name, revision, organization, yang_suite, attrs)
    return seen_modules[mod_sig]


def constructModule(name, revision, organization, yang_suite=False, attrs=dict()):
    """
    Constructs module based on default arguments. Takes array of expected arguments,
    and adds them into new module if avaiable.
    :param name: module name
    :param revision: revision of module
    :param organization: author organization
    :param yang_suite: If True, yangsuite-url is added into module as well
    :param attrs: attributes which are already avaiable from past requests.
    :return: module
    """
    mod = dict()
    for key in __module:
        if attrs.get(key) is not None:
            mod[key] = attrs[key]
        else:
            mod[key] = None
    if len(attrs) > 0:
        mod['initialized'] = True
    else:
        mod['initialized'] = False
    mod['name'] = name
    if revision == '':
        revision = '1970-01-01'
    mod['revision'] = revision
    mod['organization'] = organization
    mod['yang_suite'] = yang_suite
    return mod


def get_type_str(json):
    """
    Recreates json as str
    :param json: input json
    :return: json string.
    """
    type_str = ''
    if json.get('type') is not None:
        type_str += json['type']
    for key, val in json.items():
        if key == 'type':
            continue
        if key == 'typedef':
            type_str += get_type_str(val)
        else:
            if isinstance(val, list) or isinstance(val, dict):
                type_str += " {} {} {}".format('{', ','.join([str(i) for i in val]), '}')
            else:
                type_str += " {} {} {}".format('{', val, '}')
    return type_str


def build_tree(jsont, module):
    """
    Builds data for yang_tree.html, takes json and recursively writes out it's children.
    :param jsont: input json
    :param module: module name
    :return: (dict) with all nodes and their parameters
    """
    node = dict()
    node['text'] = jsont['name']
    if jsont.get('description') is not None:
        node['a_attr'] = dict()
        node['a_attr']['title'] = jsont['description'].replace('\n', ' ')
    else:
        node['a_attr'] = dict()
        node['a_attr']['title'] = jsont['name']
    node['data'] = {
        'schema': '',
        'type': '',
        'type_title': '',
        'type_class': 'abbrCls',
        'flags': '',
        'opts': '',
        'status': '',
        'path': '',
    }
    if jsont.get('name') == module:
        node['data']['schema'] = 'module'
    elif jsont.get('schema_type') is not None:
        node['data']['schema'] = jsont['schema_type']
    if jsont.get('type') is not None:
        node['data']['type'] = jsont['type']
        node['data']['type_title'] = jsont['type']
        if jsont.get('type_info') is not None:
            node['data']['type_title'] = get_type_str(jsont['type_info'])
    elif jsont.get('schema_type') is not None:
        node['data']['type'] = jsont['schema_type']
        node['data']['type_title'] = jsont['schema_type']
    if jsont.get('flags') is not None and jsont['flags'].get('config') is not None:
        if jsont['flags']['config']:
            node['data']['flags'] = 'config'
        else:
            node['data']['flags'] = 'no config'
    if jsont.get('options') is not None:
        node['data']['opts'] = jsont['options']
    if jsont.get('status') is not None:
        node['data']['status'] = jsont['status']
    if jsont.get('path') is not None:
        node['data']['path'] = jsont['path']
    if jsont['name'] != module and jsont.get('children') is None or len(jsont['children']) == 0:
        node['icon'] = 'glyphicon glyphicon-leaf'
        if jsont.get('path') is not None:
            node['a_attr']['href'] = "show_node/{}/{}".format(module, jsont['path'])
        node['a_attr']['class'] = 'nodeClass'
        node['a_attr']['style'] = 'color: #00e;'
    elif jsont.get('children') is not None:
        node['children'] = []
        for child in jsont['children']:
            node['children'].append(build_tree(child, module))

    return node


def get_doc(mod_obj):
    """
    Gets document-name and reference from input module object safely
    :param mod_obj: module object
    :return: documentation of module object if it exists.
    """
    try:
        doc_name = mod_obj.get('document-name')
        ref = mod_obj.get('reference')
        if ref and doc_name:
            return '<a href="' + ref + '">' + doc_name + '</a>'
        elif ref:
            return '<a href="' + ref + '">' + ref + '</a>'
        elif doc_name:
            return doc_name
    except Exception as e:
        raise Exception(e)
    return 'N/A'


def get_parent(mod_obj):
    """
    Gets parent of module object if it exists.
    :param mod_obj: module object
    :return: name of the parent of the module
    """
    try:
        bt = mod_obj.get('belongs-to')
        if not bt:
            return mod_obj.get('name') 
        return bt
    except Exception as e:
        return mod_obj.get('name')


def is_submod(mod_obj):
    """
    Find out whether module has a parent or not.
    :param mod_obj: module object 
    :return: module status
    """
    try:
        bt = mod_obj.get('belongs-to')
        if not bt:
            return False
        return True
    except Exception as e:
        return False


def build_graph(module, mod_obj, orgs, nodes, edges, edge_counts, nseen, eseen, alerts, show_rfcs, recurse=0,
                nested=False, show_subm=True, show_dir='both'):
    """
    Builds graph for impact_analysis. takes module name, and mod_obj, which has all of the modules
    dependents and dependencies.
    Goes through both dependents and dependencies and adds them to output if they are
    eligible for 
    :param module: module name
    :param mod_obj: module object
    :param orgs: organizations array
    :param nodes: nodes for output (circles)
    :param edges: lines for output
    :param edge_counts: number of edges
    :param nseen: dict
    :param eseen: dict
    :param alerts: alerts to show when something has gone awry.
    :param show_rfcs: (bool) show rfcs or not
    :param recurse: recursion level
    :param nested: (bool) module object multiple level status
    :param show_subm: (bool) submodules visibility status
    :param show_dir: (bool) directory visibility status
    :return: (dict) graph output
    """
    global found_orgs, found_mats
    is_subm = False
    if not show_subm and nested:
        module = get_parent(mod_obj)
    elif show_subm:
        is_subm = is_submod(mod_obj)

    if nested and nseen.get(module) is not None:
        return
    if mod_obj.get('organization') is not None:
        org = mod_obj.get('organization')
    else:
        org = 'independent'

    if nested > 0 and len(orgs) > 0 and not (len(orgs) == 1 and orgs[0] == ''):
        if org not in orgs:
            return

    found_orgs[org] = True
    try:
        dependents = mod_obj.get('dependents')
        dependencies = mod_obj.get('dependencies')
        mmat = get_maturity(mod_obj)
        if nested and mmat.get('olevel') == 'RATIFIED' and not show_rfcs:
            return

        color = color_gen(org)
        if found_mats.get(mmat['level']) is None:
            found_mats[mmat['level']] = [module]
        else:
            found_mats[mmat['level']].append(module)
        document = get_doc(mod_obj)
        upper_org = ''
        if org:
            upper_org = org.upper()
        nodes.append({'data': {'id': "mod_{}".format(module), 'name': module, 'objColor': color,
                               'document': document, 'sub_mod': is_subm, 'org': upper_org, 'mat': mmat['level']}})
        if edge_counts.get(module) is None:
            edge_counts[module] = 0
        nseen[module] = True
        if (show_dir == 'both' or show_dir == 'dependents') and dependents is not None:
            for moda in dependents:
                mod = moda['name']
                is_msubm = False
                mobj = get_rev_org_obj(mod, alerts)
                if mobj is None:
                    continue
                if not show_subm:
                    mod = get_parent(mobj)
                else:
                    is_msubm = is_submod(mobj)

                if eseen.get("mod_{}:mod_{}".format(module, mod)):
                    continue

                eseen["mod_{}:mod_{}".format(module, mod)] = True
                maturity = get_maturity(mobj)
                if maturity['olevel'] == 'RATIFIED' and not show_rfcs:
                    continue

                org = mobj.get('organization')
                if not org:
                    org = 'UNKNOWN'

                mcolor = color_gen(org)

                if found_mats.get(maturity['level']) is None:
                    found_mats[maturity['level']] = [mod]
                else:
                    found_mats[maturity['level']].append(mod)

                if len(orgs) > 0:
                    if org not in orgs:
                        continue

                found_orgs[org] = True

                if mmat['olevel'] == 'INITIAL' or mmat['olevel'] == 'ADOPTED':
                    edge_counts[module] += 1
                if "mod_{}".format(module) != "mod_{}".format(mod):
                    edges.append({'data': {'source': "mod_{}".format(module), 'target': "mod_{}".format(mod),
                                           'objColor': mcolor, 'org': org.upper(), 'mat': maturity['level']}})
                if recurse > 0 or recurse < 0:
                    r = recurse - 1
                    build_graph(mod, mobj, orgs, nodes, edges, edge_counts, nseen, eseen, alerts, show_rfcs, r, True, show_subm, show_dir)
                else:
                    document = get_doc(mobj)
                    nodes.append(
                        {'data': {'id': "mod_{}".format(mod), 'name': mod, 'objColor': mcolor, 'document': document,
                                  'sub_mod': is_msubm, 'org': org.upper(), 'mat': maturity['level']}})

        if (show_dir == 'both' or show_dir == 'dependencies') and dependencies:
            for moda in dependencies:
                mod = moda['name']
                is_msubm = False
                mobj = get_rev_org_obj(mod, alerts)

                if show_subm:
                    mod = get_parent(mobj)
                else:
                    is_msubm = is_submod(mobj)

                if eseen.get("mod_{}:mod_{}".format(mod, module)) is not None:
                    continue

                if eseen.get("mod_{}:mod_{}".format(module, mod)) is not None:
                    alerts.append("Loop found {} <=> {}")

                eseen["mod_{}:mod_{}"] = True
                maturity = get_maturity(mobj)
                if maturity.get('olevel') == 'RATIFIED' and not show_rfcs:
                    continue

                org = mobj.get('organization')
                if org == '':
                    org = 'UNKNOWN'
                if found_mats.get(maturity['level']) is None:
                    found_mats[maturity['level']] = [mod]
                else:
                    found_mats[maturity['level']].append(mod)

                if len(orgs) > 0:
                    if org not in orgs:
                        continue

                found_orgs[org] = True

                mcolor = color_gen(org)
                if maturity['olevel'] == 'INITIAL' or maturity['olevel'] == 'ADOPTED':
                    if not edge_counts.get(mod):
                        edge_counts[mod] = 1
                    else:
                        edge_counts[mod] += 1

                if not nested:
                    if "mod_{}".format(mod) != "mod_{}".format(module):
                        edges.append({'data': {'source': "mod_{}".format(mod), 'target': "mod_{}".format(module),
                                               'objColor': mcolor, 'org': org.upper(), 'mat': maturity['level']}})

                if nested and (recurse > 0 or recurse < 0):
                    r = recurse - 1
                    # build_graph(mod, orgs, nodes, edges, edge_counts, nseen, eseen, alerts, show_rfcs, r, True)
                elif not nested:
                    document = get_doc(mobj)
                    nodes.append(
                        {'data': {'id': "mod_{}".format(mod), 'name': mod, 'objColor': mcolor, 'document': document,
                                  'sub_mod': is_msubm, 'org': org.upper(), 'mat': maturity['level']}})
    except Exception as e:
        alerts.append("Failed to read dependency data for {}, {}".format(module, e))


def get_maturity(mod_obj, alerts=None):
    """
    Get maturity level of given module object
    :param mod_obj: module object
    :param alerts: alerts
    :return: maturity
    """
    global MATURITY_UNKNOWN, MATURITY_MAP
    maturity = {'color': MATURITY_UNKNOWN, 'level': 'N/A', 'olevel': 'N/A'}
    try:
        if mod_obj.get('maturity-level'):
            mmat = mod_obj.get('maturity-level').upper()
        else:
            mmat = ''
        if MATURITY_MAP.get(mmat) is not None:
            maturity = {'color': MATURITY_MAP[mmat], 'level': mmat, 'olevel': mmat}
        if mmat == 'INITIAL' or mmat == 'ADOPTED':
            cstatus = get_compile_status(mod_obj)
            if cstatus == 'failed':
                level = 'COMPILATION FAILED'
                maturity = {'color': MATURITY_MAP[level], 'level': level, 'olevel': mmat}
    except Exception as e:
        raise Exception(e)
    return maturity


def get_compile_status(mod_obj):
    """
    Gets compilation status of give module object
    :param mod_obj: module object
    :return: compilation status
    """
    try:
        cstatus = mod_obj.get('compilation-status')
        if cstatus is None:
            return ''
        return cstatus
    except Exception as e:
        return ''


def color_gen(org):
    """
    Color generator for impact_analysis website, dependent organization and it's arguments.
    Makes request to local database
    :param org: organization
    :return: color
    """
    global NUM_STEPS, CUR_STEP, ORG_CACHE
    if org:
        org = org.upper()
    if ORG_CACHE.get(org) is not None:
        return ORG_CACHE[org]
    if NUM_STEPS == -1:
        try:
            row = modules.objects.values('organization').order_by('organization').distinct().count()
            NUM_STEPS = row + 1
        except Exception as e:
            NUM_STEPS = 33
            raise Exception(e)
    r = -1
    g = -1
    b = -1
    h = CUR_STEP / NUM_STEPS
    i = int(h * 6)
    f = h * 6 - i
    q = 1 - f
    result = i % 6
    if result == 0:
        r = 1
        g = f
        b = 0
    elif result == 1:
        r = q
        g = 1
        b = 0
    elif result == 2:
        r = 0
        g = 1
        b = f
    elif result == 3:
        r = 0
        g = q
        b = 1
    elif result == 4:
        r = f
        g = 0
        b = 1
    elif result == 5:
        r = 1
        g = 0
        b = q
    c = '#' + ('00' + hex(int(r * 255)))[-2:] + ('00' + hex(int(g * 255)))[-2:] + ('00' + hex(int(b * 255)))[-2:]
    c = c.replace('x', '0')
    ORG_CACHE[org] = c
    CUR_STEP += 1
    return c


def moduleFactoryFromSearch(search):
    """
    Creates module based on api search. Used only with ietf_wg in impact_analysis.
    :param search: search term
    :return: module object
    """
    mod_objs = []
    global seen_modules
    url = 'https://yangcatalog.org/api/search/{}'.format(search)
    response = requests.get(url, headers={'Content-type': 'application/json', 'Accept': 'application/json'})
    result = json.loads(response.text)
    for mod in result['yang-catalog:modules']['module']:
        mod_sig = "{}@{}/{}".format(mod['name'], mod['revision'], mod['organization'])
        seen_modules[mod_sig] = constructModule(mod['name'], mod['revision'], mod['organization'], False, mod)
        mod_objs.append(seen_modules[mod_sig])

    return mod_objs


def asort(d):
    """
    Sort dictionary
    :param d: (dict)
    :return: returns sorted dictionary
    """
    return sorted(d.items(), key=lambda x: x[1], reverse=True)


def get_latest_mod(module, alerts, depth=1):
    """
    Gets latest version of module.
    :param module: module name
    :param alerts: alerts
    :param depth: depth how far should function search when looking for latest module
    :return: module
    """
    try:
        sth = modules.objects.values('revision').filter(module=module).order_by('-revision').distinct()[:depth]
        i = 0
        for row in sth:
            if row and row.get('revision'):
                return "{}@{}".format(module, row['revision'])

    except Exception as e:
        raise Exception("Failed to get revision for {}".format(module))
    return module

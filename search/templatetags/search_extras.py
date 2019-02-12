from django import template
from django.utils.html import escape
from django.conf import settings
import logging
import json
import re

logger = logging.getLogger(__name__)
register = template.Library()

__module = [
    'name', 'revision', 'organization', 'ietf', 'namespace', 'schema', 'generated-from', 'maturity-level',
    'document-name', 'author-email', 'reference', 'module-classification', 'compilation-status',
    'compilation-result', 'prefix', 'yang-version', 'description', 'contact', 'module-type', 'belongs-to',
    'tree-type', 'yang-tree', 'expires', 'expired', 'submodule', 'dependencies', 'dependents',
    'semantic-version', 'derived-semantic-version', 'implementations'
]


@register.filter(name='array_map')
def array_map(array):
    """
    Adjust naming for given array.
    :param array: array
    :return: adjusted array
    """
    output = ','.join(map(lambda x: 'node#mod_' + x, array))
    return output


@register.filter(name='unescape')
def unescape(str):
    """
    Removes some of the html characters and replaces them.
    :param str: Input string
    :return: unescaped string
    """
    str = str.replace('\n', "\n\t")
    str = str.replace('\r', "\r")
    str = str.replace('\t', "\t")
    str = str.replace('\\\\', '\\')
    return str


@register.filter(name='implode')
def implode(list):
    """
    Takes list and returns standardized version of it.
    :param list: list
    :return: standardized list
    """
    return ', '.join([str(i) for i in list])


@register.filter(name='lower')
def lower(boolean):
    """
    Change python bool (True, False) to string which is recognized
    by javascript
    :param boolean: bool 
    :return: bool in string
    """
    if boolean:
        return 'true'
    else:
        return 'false'


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Returns value in string in upper form
    :param dictionary: dict
    :param key: key
    :return: value
    """
    return dictionary.get(key.upper())


@register.filter(name='norm_path')
def norm_path(path):
    """
    Add slash for url recognition
    :param path: (string) path
    :return: normalized path
    """
    # path = path.replace('/', '%')
    path += '/'
    return path


@register.filter(name='print_properties')
def print_properties(node):
    """
    Print properties for show_node webpage
    :param node: node with properties
    :return: html output
    """
    str = ''
    str += "<i>// From : {}@{}</i>\r\n\r\n".format(node.get('module'), node.get('revision'))
    str += "<b>{}</b> {}".format(node.get('statement'), node.get('argument')) + ' {\r\n'
    str += dissolve(json.loads(node.get('properties')), '\t')
    str += '}'
    return str


def dissolve(properties, indent = '\t'):
    """
    Recursive function for dissecting properties for output.
    Handles children properties
    :param properties: node properties
    :param indent: tab indent for multilevel writeout
    :return: html output
    """
    str = ''
    for property in properties:
        for key, val in property.items():
            if val.get('value') is not None and val.get('value') is not '':
                str += '{}<b>{}</b> {}'.format(indent, key, unescape_str(val.get('value'), indent))
            else:
                str += "{}<b>{}</b> ".format(indent, key)
            if val.get('has_children') and len(val.get('children')) == 0:
                str += ' {' + '\n{0}\t...\n{0}'.format(indent) + "}\n"
            elif len(val.get('children')) > 0:
                str += " {\n"
                str += dissolve(val['children'], indent + "\t")
                str += "\n{}".format(indent) + "}\n"
            else:
                str += ";\n"
    return str


@register.filter(name='search_results')
def search_results(results, search_columns):
    html = ''
    if results:
        for result in results:
            html += '<tr>'
            if "Name" in search_columns:
                path = result['path'].replace('?', '%3F')
 #               for type_part in re.findall(r'\?[^/]*', result['path']):
  #                  path = path.replace(type_part, '')
                html += '<td> <a href="/yang-search/show_node/{}/{}/{}">{}</a></td>'\
                    .format(result['name'], path, result['revision'], result['node_name'])
            if "Revision" in search_columns:
                html += '<td>{}</td>'.format(result['revision'])
            if "Schema Type" in search_columns:
                html += '<td>{}</td>'.format(result['type'])
            if "Path" in search_columns:
                html += '<td>{}</td>'.format(result['path'])
            if "Module" in search_columns:
                html += '<td>{}<br/>'.format(result['name'])
                html += '<span style = "font-size: small">'
                html += '(<a href="/yang-search/module_details/{}">'.format(result['name'])
                html += '<img src="/yang-search/static/img/details.png" border="0" title="Module Details for {}" > Module Details </a>'.format(result['name'])
                html += '|<a href="/yang-search/yang_tree/{}" >'.format(result['name'])
                html += '<img border="0" src="/yang-search/static/img/leaf.png" title="Tree View for {}" >'.format(result['name'])
                html += 'Tree View </a>|'
                html += '<a href="/yang-search/impact_analysis/{}" >'.format(result['name'])
                html += '<img src="/yang-search/static/img/impact.png" border="0" title="Impact Analysis for {}" >'.format(result['name'])
                html += 'Impact Analysis </a>) </span> </td>'
            if "Origin" in search_columns:
                html += '<td> {} </td>'.format(result['origin'])
            if "Organization" in search_columns:
                html += '<td> {} </td>'.format(result['organization'])
            if "Maturity" in search_columns:
                html += '<td> {} </td>'.format(result['maturity'])
            if "Imported By # Modules" in search_columns:
                html += '<td> {} </td>'.format(result['dependents'])
            if "Compilation Status" in search_columns:
                if result['compile_status']:
                    html += '<td> {} </td>'.format(result['compile_status'])
                else:
                    html += '<td> N/A </td>'
            if "Description" in search_columns:
                html += '<td> {} </td>'.format(result['description'])
            html += '</tr>'
    return html


@register.filter(name='print_cells')
def print_cells(module_details):
    """
    Function for module_details webpage.
    Output is pure html.
    Taked module details, and transforms them into comprehensive output
    :param module_details: module details
    :return: html output
    """
    if module_details:
        html = ''
        for key in __module:
            help_text = '{}_ht'.format(key)
            html += '<tr>' + '\n'
            html += '<td style="text-align: right"><b>{} : </b>'.format(key)
#            html += '<img src="/yang/static/img/help.png" border="0" data-html="true" data-toggle="tooltip" title="{}"/></td>' \
            html += '<img src="' + settings.STATIC_URL + '/img/help.png" border="0" data-html="true" data-toggle="tooltip" title="{}"/></td>' \
                .format(module_details[help_text])
            inner_html = print_cell(module_details[key], key, module_details['name'])
            html += inner_html
            html += '</tr>\n'
        return html
    else: 
        return


def print_cell(value, key, name, pkey='', isDeviation=False):
    """
    Takes key and value, and based on their value, changes the way they appear
    in the final html list
    :param value: value from module details dict
    :param key: key from module details dict
    :param name: name of the current module
    :param pkey: primary key
    :return: one entry from html list
    """
    if key == 'deviation':
        isDeviation = True
    html = ''
    if not isinstance(value, list) and not isinstance(value, dict):
        if value == False:
            value = 'false'
        elif value == True:
            value = 'true'
        nval = re.sub(r'(((http)(s)?://)|mailto:)[a-zA-Z0-9.?&_/\-@+]+', r'<a href="\g<0>">\g<0></a>',
                      escape(value).replace('&gt;', '>')).replace("\n", "<br/>\n")
        matches = re.findall(r"([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+([.][a-zA-Z0-9-]+)*)(?![^<]*>|[^<>]*</)",
                             nval)
        if matches:
            for match in matches:
                match = match[0]
                nval = nval.replace(match, '<a href="mailto:{0}">{0}</a>'.format(match))
        if key == 'name' and isDeviation:
            html += '<td> <a href="/yang-search/module_details/?module={0}">{0}</a></td>'.format(value)
        else:
            html += '<td>{}</td>'.format(nval)
    elif key == 'revision':
        html += '<td><div class="dropdown">'
        for nv in value:
            if 'current@' in nv:
                html += '<button class="btn btn-default dropdown-toggle" type="button" data-toggle="dropdown">{}'.format(nv.split('@')[1])
                break
        html += '<span class="caret"></span></button>'
        html += '<ul class="dropdown-menu">'
        for nv in value:
           if 'current@' in nv:
               html += '<li class="active"><a href="?module={}@{}">{}</a></li>'.format(name, nv.split('@')[1], nv.split('@')[1])
           else:
               html += '<li><a href="?module={}@{}">{}</a></li>'.format(name, nv, nv)
        html += '</ul></div></td>'
    else:
        npk = None
        msg = 'Click to toggle "' + key + '" details.'
        npk = key
        if key not in __module:
            collapse = "collapse in"
        else:
            collapse = "collapse"
        if pkey:
            msg = 'Click to toggle {} {} details.'.format(pkey, key)
        html += '<td><div><a href = "#table-' + key
        html += '" class="accordion-toggle" data-toggle="collapse">{}</a></div>'.format(msg)
        html += '<div class="accordion-body {}" id="table-{}"><table class ="table table-responsive" cellspacing="0">' \
            .format(collapse, key)
        html += '<tbody>'
        if isinstance(value, dict):
            for nk, nv in value.items():
                html += '<tr>'
                html += '<td><b>{} : </b></td>'.format(nk)

                html += print_cell(nv, nk, name, npk, isDeviation)
                html += '</tr>'
        else:
            i = 0
            for nv in value:
                nk = i
                html += '<tr>'
                html += '<td><b>{}: </b></td>'.format(nk)
                html += print_cell(nv, str(nk), name, npk, isDeviation)
                i += 1
                html += '</tr>'
        html += '</tbody>'
        html += '</table></div>'
        html += '</td>'
    return html


def unescape_str(str, indent):
    """
    Unescape string function which handles email addresses and urls
    :param str: string
    :param indent: indent
    :return: string
    """
    indent += "\t"
    str = str.replace("''", "'")
    str = str.replace('\\n', '</br>                ')
    str = str.replace('\r', "\r")
    str = str.replace('\t', "\t")
    str = str.replace('\\\\', '\\')
    if re.search('[\\\\^\|\{\}\?\+\*\[\]]', str) and "'" not in str:
        str = "'" + str + "'"
    elif re.search('\s', str) or "'" in str and re.search('[\\\\^\|\{\}\?\+\*\[\]]', str):
        str = '"' + str + '"'
    return str


@register.filter(name='nodify')
def nodify(n):
    """
    Modifies string to contain node#mod_
    :param n: string
    :return: string
    """
    return 'node#mod_{}'.format(n)

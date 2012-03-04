import collections
import os
import os.path
import sys
import re
import xml.etree.ElementTree
import xml.etree.ElementInclude


VALID_CATEGORY_REGEXP = re.compile(r'[0-9]\.[0-9]$|GL_[A-Za-z0-9_]+$')
ALLOWED_NESTINGS = (('OpenGLAPI', 'category'),
                    ('OpenGLAPI', 'OpenGLAPI'),
                    ('category', 'enum'),
                    ('category', 'type'),
                    ('category', 'function'),
                    ('function', 'param'),
                    ('function', 'glx'),
                    ('function', 'return'),
                    ('enum', 'size'),
                    )
BASE_TYPES = ()
RECOGNIZED_STRUCTS = ('_cl_context', '_cl_event')


error_found = False


def error(desc):
    global error_found
    error_found = True
    print 'Error: {0}'.format(desc)


def short_desc(elem):
    if 'name' in elem.attrib:
        return '<{0} name="{1}">'.format(elem.tag, elem.attrib['name'])
    else:
        return '<{0}>'.format(elem.tag)


def check_nesting(elem):
    for sub_elem in elem.findall('*'):
        if (elem.tag, sub_elem.tag) not in ALLOWED_NESTINGS:
            error('{0} nested inside {1}'.format(
                    short_desc(sub_elem), short_desc(elem)))
        check_nesting(sub_elem)


def check_categories(api_xml):
    for category_xml in api_xml.findall('.//category'):
        name = category_xml.attrib['name']
        if not VALID_CATEGORY_REGEXP.match(name):
            error('Invalid category: {0!r}'.format(name))


def check_types(api_xml):
    types = set()
    for type_xml in api_xml.findall('.//type'):
        name = type_xml.attrib['name']
        if name.startswith('GL'):
            error('Invalid type name {0!r}'.format(name))
        types.add('GL' + name)
    print 'Found {0} unique type names'.format(len(types))
    return types


def check_enum_value(name, value):
    if value.endswith('u'):
        # Value ending in u is ok--this just tells the compiler the
        # value is unsigned.
        value = value[:-1]
    try:
        value_int = int(value, 0)
        return
    except ValueError:
        pass
    error("Don't know how to interpret value of enum {0} ({1!r})".format(
            name, value))


def check_enum_name(name):
    if name.startswith('GL_'):
        error('invalid enum name {0!r}'.format(name))


def check_enums(api_xml):
    name_to_values_dict = collections.defaultdict(set)
    for enum_xml in api_xml.findall('.//enum'):
        name = enum_xml.attrib['name']
        value = enum_xml.attrib['value']
        check_enum_value(name, value)
        check_enum_name(name)
        name_to_values_dict[name].add(value)
    print 'Found {0} unique enum names'.format(len(name_to_values_dict))
    for name in sorted(name_to_values_dict.keys()):
        values = name_to_values_dict[name]
        if len(values) != 1:
            error_desc = 'inconsistent definitions of enum {0!r}:'.format(name)
            for value in values:
                error_desc += '\n  {0}'.format(value)
            error(error_desc)


def check_function_name(name):
    if name.startswith('gl'):
        error('invalid function name {0!r}'.format(name))


def check_type_usage(function, typ, gl_types):
    type_components = typ.replace('*', ' * ').split(' ')
    type_components = [x for x in type_components if x != '']
    if len(type_components) == 0:
        error('{0} uses empty type'.format(short_desc(function)))
    i = 0
    while i < len(type_components):
        component = type_components[i]
        if (component in ('const', '*') or
            component in gl_types or
            component in BASE_TYPES):
            pass
        elif component == 'struct':
            i += 1
            if i == len(type_components):
                error('{0} uses invalid type {1!r}'.format(
                        short_desc(function), typ))
                break
            else:
                if type_components[i] not in RECOGNIZED_STRUCTS:
                    error('{0} uses unrecognized struct {1}'.format(
                            short_desc(function), type_components[i]))
        else:
            error('{0} uses unrecognized type {1!r}'.format(
                    short_desc(function), component))
        i += 1


def check_functions(api_xml, gl_types):
    name_to_xml_dict = collections.defaultdict(list)
    for function_xml in api_xml.findall('.//function'):
        name = function_xml.attrib['name']
        check_function_name(name)
        name_to_xml_dict[name].append(function_xml)
        for param_xml in function_xml.findall('param'):
            check_type_usage(function_xml, param_xml.attrib['type'],
                             gl_types)
        return_xmls = function_xml.findall('return')
        if len(return_xmls) > 1:
            error('{0} declares multiple returns'.format(
                    short_desc(function_xml)))
        for return_xml in return_xmls:
            check_type_usage(function_xml, return_xml.attrib['type'],
                             gl_types)
    print 'Found {0} unique function names'.format(len(name_to_xml_dict))


if __name__ == '__main__':
    file_to_parse = sys.argv[1]
    os.chdir(os.path.dirname(file_to_parse))
    basename = os.path.basename(file_to_parse)
    root = xml.etree.ElementTree.parse(basename).getroot()
    xml.etree.ElementInclude.include(root)
    check_nesting(root)
    check_categories(root)
    gl_types = check_types(root)
    check_enums(root)
    check_functions(root, gl_types)
    if error_found:
        exit(1)

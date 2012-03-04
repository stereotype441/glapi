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


def short_desc(elem):
    if 'name' in elem.attrib:
        return '<{0} name="{1}">'.format(elem.tag, elem.attrib['name'])
    else:
        return '<{0}>'.format(elem.tag)


def check_nesting(elem):
    ok = True
    for sub_elem in elem.findall('*'):
        if (elem.tag, sub_elem.tag) not in ALLOWED_NESTINGS:
            ok = False
            print 'Error: {0} nested inside {1}'.format(
                short_desc(sub_elem), short_desc(elem))
        ok = check_nesting(sub_elem) and ok
    return ok


def check_categories(api_xml):
    ok = True
    for category_xml in api_xml.findall('.//category'):
        name = category_xml.attrib['name']
        if not VALID_CATEGORY_REGEXP.match(name):
            ok = False
            print 'Invalid category: {0!r}'.format(name)
    return ok


def check_enum_value(name, value):
    if value.endswith('u'):
        # Value ending in u is ok--this just tells the compiler the
        # value is unsigned.
        value = value[:-1]
    try:
        value_int = int(value, 0)
        return True
    except ValueError:
        pass
    print "Don't know how to interpret value of enum {0} ({1!r})".format(
        name, value)
    return False


def check_enums(api_xml):
    ok = True
    name_to_values_dict = collections.defaultdict(set)
    for enum_xml in api_xml.findall('.//enum'):
        name = enum_xml.attrib['name']
        value = enum_xml.attrib['value']
        ok = check_enum_value(name, value) and ok
        name_to_values_dict[name].add(value)
    print 'Found {0} enum declarations'.format(len(name_to_values_dict))
    for name in sorted(name_to_values_dict.keys()):
        values = name_to_values_dict[name]
        if len(values) != 1:
            ok = False
            print 'Error: inconsistent definitions of enum {0!r}:'.format(name)
            for value in values:
                print '  {0}'.format(value)
    return ok


if __name__ == '__main__':
    file_to_parse = sys.argv[1]
    os.chdir(os.path.dirname(file_to_parse))
    basename = os.path.basename(file_to_parse)
    root = xml.etree.ElementTree.parse(basename).getroot()
    xml.etree.ElementInclude.include(root)
    ok = True
    ok = check_nesting(root) and ok
    ok = check_categories(root) and ok
    ok = check_enums(root) and ok
    if not ok:
        exit(1)

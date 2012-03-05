import collections
import json
import os
import xml.etree.ElementTree
import xml.etree.ElementInclude

# The JSON output format is as follows:
# {
#   "categories": {
#     <category name>: {
#       "enums": <list of enum names, without "GL_" prefix>,
#       "functions": <list of function names, without "gl" prefix>,
#       "types": <list of type names, without "GL" prefix>
#       "kind": <"GL" for a GL version, "extension" for an extension>,
#       "gl_10x_version": <For a GL version, version number times 10>,
#       "extension_name" <For an extension, name of the extension>
#     }, ...
#   },
#   "enums": {
#     <enum name, without "GL_" prefix>: {
#       "value_int": <value integer>
#       "value_str": <value string>
#     }, ...
#   },
#   "functions": {
#     <function name, without "gl" prefix>: {
#       "param_names": <list of param names>,
#       "param_types": <list of param types, canonicalized>,
#       "return_type": <canonicalized type, "void" if no return>
#     }, ...
#   },
#   "function_alias_sets": {
#     <list of synonymous function names>, ...
#   },
#   "types": {
#     <type name, without "GL" prefix>: {}, ...
#   }
# }


def normalize_type(typ):
    tokens = [token for token in typ.replace('*', ' * ').split(' ')
              if token != '']
    return ' '.join(tokens)


def decode_enum_value(value_str):
    if value_str.endswith('u'):
        value_str = value_str[:-1]
    return int(value_str, 0)


def jsonizer(obj):
    if type(obj) in (set, frozenset):
        return sorted(obj)
    else:
        raise Exception('jsonizer({0})'.format(type(obj)))


# Data structure keeping track of which function names are known, and
# which names are synonymous with which other names.
class SynonymMap(object):
    def __init__(self):
	# __name_to_synonyms maps from a function name to the set of
	# all names that are synonymous with it (including itself).
	self.__name_to_synonyms = {}

    # Add a single function name which is not (yet) known to be
    # synonymous with any other name.  No effect if the function name
    # is already known.
    def add_singleton(self, name):
	if name not in self.__name_to_synonyms:
	    self.__name_to_synonyms[name] = frozenset([name])
	return self.__name_to_synonyms[name]

    # Add a pair of function names, and note that they are synonymous.
    # Synonymity is transitive, so if either of the two function names
    # previously had known synonyms, all synonyms are combined into a
    # single set.
    def add_alias(self, name, alias):
	name_ss = self.add_singleton(name)
	alias_ss = self.add_singleton(alias)
	combined_set = name_ss | alias_ss
	for n in combined_set:
	    self.__name_to_synonyms[n] = combined_set

    # Get a list of lists of synonymous functions.
    def get_synonym_sets(self):
        return frozenset(self.__name_to_synonyms.values())


class Api(object):
    def __init__(self):
        self.categories = {}
        self.enums = {}
        self.functions = {}
        self.function_aliases = SynonymMap()
        self.types = {}

    def read_xml(self, root):
        for category_xml in root.findall('.//category'):
            category_name = category_xml.attrib['name']
            if category_name in self.categories:
                raise Exception(
                    'Duplicate category {0!r}'.format(category_name))
            category = { 'enums': set(),
                         'functions': set(),
                         'types': set() }
            try:
                gl_version = float(category_name)
                category['kind'] = 'GL'
                category['gl_10x_version'] = int(round(10*gl_version))
            except ValueError:
                category['kind'] = 'extension'
                category['extension_name'] = category_name
            self.categories[category_name] = category
            for enum_xml in category_xml.findall('enum'):
                enum_name = enum_xml.attrib['name']
                enum_value = enum_xml.attrib['value']
                if enum_name in self.enums:
                    if self.enums[enum_name]['value_str'] != enum_value:
                        raise Exception(
                            'Inconsistent definitions for enum '
                            '{0!r}'.format(enum_name))
                else:
                    self.enums[enum_name] = {
                        'value_str': enum_value,
                        'value_int': decode_enum_value(enum_value)
                        }
                category['enums'].add(enum_name)
            for function_xml in category_xml.findall('function'):
                function_name = function_xml.attrib['name']
                return_xmls = function_xml.findall('return')
                if len(return_xmls) == 0:
                    return_type = 'void'
                elif len(return_xmls) == 1:
                    return_type = normalize_type(return_xmls[0].attrib['type'])
                else:
                    raise Exception(
                        'Too many return types for function {0!r} in '
                        'category {1!r}'.format(
                            function_name, category_name))
                param_types = []
                param_names = []
                for param_xml in function_xml.findall('param'):
                    param_types.append(
                        normalize_type(param_xml.attrib['type']))
                    param_names.append(param_xml.attrib['name'])
                if function_name in self.functions:
                    if (self.functions[function_name]['return_type'] !=
                        return_type):
                        raise Exception(
                            'Inconsistent return types for function '
                            '{0!r}'.format(
                                function_name))
                    if (self.functions[function_name]['param_types'] !=
                        param_types):
                        raise Exception(
                            'Inconsistent param types for function '
                            '{0!r}'.format(
                                function_name))
                else:
                    self.functions[function_name] = {
                        'param_names': param_names,
                        'param_types': param_types,
                        'return_type': return_type
                        }
                if 'alias' in function_xml.attrib:
                    self.function_aliases.add_alias(
                        function_name, function_xml.attrib['alias'])
                else:
                    self.function_aliases.add_singleton(function_name)
                category['functions'].add(function_name)
            for type_xml in category_xml.findall('type'):
                type_name = type_xml.attrib['name']
                if type_name in self.types:
                    # If we stored any information about types, this
                    # is where we would check that the information was
                    # consistent.
                    pass
                else:
                    self.types[type_name] = {}
                category['types'].add(type_name)

    def to_json(self):
        return json.dumps({
                'categories': self.categories,
                'enums': self.enums,
                'functions': self.functions,
                'function_alias_sets':
                    self.function_aliases.get_synonym_sets(),
                'types': self.types,
                }, indent = 2, sort_keys = True, default = jsonizer)


if __name__ == '__main__':
    api = Api()
    os.chdir(os.path.join(os.path.dirname(__file__), 'glapi'))
    root = xml.etree.ElementTree.parse('gl_API.xml').getroot()
    xml.etree.ElementInclude.include(root)
    api.read_xml(root)
    print api.to_json()

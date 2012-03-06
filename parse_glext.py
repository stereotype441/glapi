# TODO: get rid of hardcoded paths.


import json
import os
import re


FUNCTION_REGEXP = re.compile('(?P<rettype>.+) APIENTRY (?P<name>.+)\\((?P<args>[^)]+)\\);')


class HeaderParser(object):
    def __init__(self):
        self.started = False
        self.category_name = None
        self.categories = {}
        self.enums = {}
        self.functions = {}
        self.skip_nesting = 0

    def start_category(self, category_name):
        self.category_name = category_name
        if category_name not in self.categories:
            self.categories[category_name] = { 'enums': set(), 'functions': set() }

    def handle_function(self, decl):
        m = FUNCTION_REGEXP.match(decl)
        if not m:
            raise Exception('{0!r}'.format(decl))
        rettype = ' '.join(m.group('rettype').replace('*', ' * ').split())
        name = m.group('name').strip()
        if name.startswith('gl'):
            name = name[2:]
        else:
            raise Exception('{0!r}'.format(decl))
        param_types = []
        param_names = []
        if m.group('args').strip() != 'void':
            for param in m.group('args').split(','):
                tokens = param.replace('*', ' * ').split()
                if len(tokens) < 2:
                    raise Exception('{0!r}'.format(decl))
                param_types.append(' '.join(tokens[:-1]))
                param_names.append(tokens[-1])
        self.categories[self.category_name]['functions'].add(name)
        if name not in self.functions:
            self.functions[name] = {
                'return_type': rettype,
                'param_types': param_types,
                'param_names': param_names
                }

    def handle_line(self, line):
        line = line.strip()
        if line == '':
            return
        if not self.started:
            if line.startswith('/**'):
                self.started = True
            return
        if self.skip_nesting != 0:
            if line.startswith('#if'):
                self.skip_nesting += 1
            elif line.startswith('#endif'):
                self.skip_nesting -= 1
            return
        if line == '#ifndef GLEXT_64_TYPES_DEFINED':
            self.skip_nesting = 1
            return
        if self.category_name is None:
            if line.startswith('#ifndef GL_VERSION_'):
                self.start_category(line[19:].replace('_', '.'))
                return
            if line.startswith('#ifndef GL_'):
                self.start_category(line[8:])
                return
        if line.startswith('#define GL_'):
            def_split = line[11:].split()
            if len(def_split) == 2:
                enum_name, enum_value = def_split
                self.enums[enum_name] = { 'value_str': enum_value }
                self.categories[self.category_name]['enums'].add(enum_name)
                return
        if line == '#endif':
            self.category_name = None
            return
        if line.startswith('/* Reuse tokens from '):
            # TODO
            return
        if line.startswith('typedef '):
            # TODO
            return
        if line.startswith('struct '):
            # TODO
            return
        if line.startswith('GLAPI '):
            self.handle_function(line[6:])
            return
        if line.startswith('/* reuse GL_'):
            reuse_split = line[12:].split()
            if len(reuse_split) == 2 and reuse_split[1] == '*/':
                enum_name = reuse_split[0]
                self.categories[self.category_name]['enums'].add(enum_name)
            return


def compare_data(glapi_json, parser):
    for thing in ('categories', 'enums', 'functions'):
        print '{0} in JSON but not in glext.h: {1}'.format(
            thing,
            ', '.join(sorted(set(glapi_json[thing].keys())
                             - set(getattr(parser, thing).keys()))))


if __name__ == '__main__':
    parser = HeaderParser()
    with open(os.path.expanduser('~/mesa/include/GL/glext.h'), 'r') as f:
        for line in f:
            parser.handle_line(line)
    with open(os.path.expanduser('~/tmp/glapi.json'), 'r') as f:
        glapi_json = json.load(f)
    compare_data(glapi_json, parser)

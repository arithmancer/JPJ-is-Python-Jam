"""
path.py
part of 'JPJ is Python Jam'
See README for license
--------------------------------------------------------------------------------
"""

import os.path

import jam.exceptions

def splitgrist(path):
    if path[0] == '<':
        g = path[1:].partition('>')
        if g[1] == '>':
            return (g[0], g[2])
    return ('', path)

def splitmodule(path):
    if path and path[-1] == ')':
        m = path[:-1].rpartition('(')
        if m[1] == '(':
            return (m[0], m[2])
    return (path, '')

class JamPath:
    def __init__(self, **kw):
        self.edit_dictionary = {'G': None, 'R': None, 'D': None, 'B': None, 'S': None, 'M': None, 'E': None, 'J': None}
        self.active_path = False
        self.path_mask = {'G': False, 'D': False, 'B': False, 'S': False, 'M': False, 'P': False}
        self.active_mask = False
        self.case = 0
        for key in kw:
            self[key] = kw[key]

    def __setitem__(self, key, value):
        if value == None:
            if key == 'L':
                if self.case != 0:
                    raise jam.exceptions.JamSyntaxError
                self.case = -1
            elif key == 'U':
                if self.case != 0:
                    raise jam.exceptions.JamSyntaxError
                self.case = 1
            elif key in ('E', 'J'):
                self.edit_dictionary[key] = ''
            elif key in self.path_mask:
                if self.path_mask[key]:
                    raise jam.exceptions.JamSyntaxError
                self.path_mask[key] = True
                if key != 'P':
                    self.active_mask = True
                self.active_path = True
        else:
            if key in self.edit_dictionary:
                if self.edit_dictionary[key] != None:
                    raise jam.exceptions.JamSyntaxError
                self.edit_dictionary[key] = value
                if key not in ('E', 'J'):
                    self.active_path = True

    def __call__(self, value):
        if (value == []) and (self.edit_dictionary['E'] != None):
            value.append(self.edit_dictionary['E'])
        if self.case < 0:
            value = [ t.lower() for t in value ]
        elif self.case > 0:
            value = [ t.upper() for t in value ]
        if self.edit_dictionary['J'] != None:
            value = [ self.edit_dictionary['J'].join(value) ]

        if self.active_path:
            result = []
            for path in value:
                path_dictionary = {}
                (path_dictionary['G'], path) = splitgrist(path)
                (path, path_dictionary['M']) = splitmodule(path)
                (path_dictionary['D'], path) = os.path.split(path)
                (path_dictionary['B'], path_dictionary['S']) = os.path.splitext(path)

                for key in path_dictionary:
                    if self.edit_dictionary[key] != None:
                        path_dictionary[key] = self.edit_dictionary[key]

                if self.edit_dictionary['R']:
                    if (self.edit_dictionary['R'] != '.') and ((not path_dictionary['D']) or (path_dictionary['D'][0] != '/')):
                        path_dictionary['D'] = os.path.join(self.edit_dictionary['R'], path_dictionary['D'])

                if self.path_mask['P']:
                    (path_dictionary['B'], path_dictionary['S'], path_dictionary['M']) = ('', '', None)
                if self.active_mask:
                    for key in path_dictionary:
                        if not self.path_mask[key]:
                            path_dictionary[key] = ''

                path = os.path.join(path_dictionary['D'], path_dictionary['B'] + path_dictionary['S'])
                if path_dictionary['G']:
                    path = '<' + path_dictionary['G'] + '>' + path
                if path_dictionary['M']:
                    path = path + '(' + path_dictionary['M'] + ')'

                result.append(path)
        else:
            result = value

        return result

class JamStat:
    def __init__(self):
        self.archives = {}

    def _read_archive(self, path):
        if path not in self.archives:
            entries = {}
            if os.path.exists(path):
                with open(path, mode='rb') as f:
                    if f.read(8) == b'!<arch>\x0a':
                        position = 8
                        while 1:
                            header = f.read(60)
                            if (len(header) < 60) or (header[-2:] != b'\x60\x0a'):
                                break
                            filename = header[0:16].decode('utf-8').rstrip()
                            if filename[:3] == '#1/':
                                length = int(filename[3:])
                                filename = f.read(length).decode('utf-8').rstrip('\x00')
                            timestamp = int(header[16:28].decode('ascii').rstrip())
                            entries[filename] = timestamp
                            size      = int(header[48:58].decode('ascii').rstrip())
                            position += (60 + size)
                            f.seek(position)
            self.archives[path] = entries                            

    def exists(self, path):
        (archive, module) = splitmodule(path)
        if module:
            self._read_archive(archive)
            exists = (module in self.archives[archive])
        else:
            exists = os.path.exists(path)
        return exists

    def timestamp(self, path):
        (archive, module) = splitmodule(path)
        if module:
            self._read_archive(archive)
            timestamp = self.archives[archive][module]
        else:
            timestamp = os.path.getmtime(path)
        return timestamp
                

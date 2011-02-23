import time
import os

class Variables:
    def __init__(self, tag):
        self.variable_dictionary = {}
        self.tag = tag

    def __contains__(self, name):
        return (name in self.variable_dictionary)

    def set(self, name, operation, value):
        if operation == '=':
            self.variable_dictionary[name] = value
        else:
            current_value = []
            if name in self.variable_dictionary:
                current_value = self.variable_dictionary[name]
            if operation == '+=':
                self.variable_dictionary[name] = current_value + value
            elif operation == '?=':
                if not current_value:
                    self.variable_dictionary[name] = value

    def get(self, name):
        if name == '<':
            name = '1'
        elif name == '>':
            name = '2'
        if name in self.variable_dictionary:
            return self.variable_dictionary[name]
        return None

    def dump(self, writable, exclude):
        print('Scope:', self.tag, 'writable =', writable)
        if self.tag not in exclude:
            for name in self.variable_dictionary:
                print(name,'=',self.variable_dictionary[name])

class VariableStack:
    def __init__(self):
        variables = Variables('global')

        variables.set('MAC', '=', [])
        variables.set('NT', '=', [])
        variables.set('OS2', '=', [])
        variables.set('UNIX', '=', [])
        variables.set('VMS', '=', [])
        variables.set('JAMUNAME', '=', [])
        if os.name == 'mac':
            variables.set('MAC', '=', ['true'])
            variables.set('OS', '=', ['MAC'])
        elif os.name == 'nt':
            variables.set('NT', '=', ['true'])
            variables.set('OS', '=', ['NT'])
        elif os.name == 'os2':
            variables.set('OS2', '=', ['true'])
            variables.set('OS', '=', ['OS2'])
        elif os.name == 'posix':
            variables.set('UNIX', '=', ['true'])
            un = list(os.uname())
            un.reverse()
            variables.set('JAMUNAME', '=', un)
            if un:
                variables.set('OSVER', '=', un[2:3])
                if un[0] == 'i386':
                    variables.set('OSPLAT', '=', ['X86'])
                elif un[0] == 'ppc':
                    variables.set('OSPLAT', '=', ['PPC'])
                if un[4] == 'Darwin':
                    variables.set('OS', '=', ['MACOSX'])

        variables.set('JAMDATE', '=', [ time.strftime('%a %b %d %H:%M:%S %Y', time.gmtime()) ])
        variables.set('JAMVERSION', '=', [ '2.5.2' ])
        variables.set('JPJ', '=', ['true'])
        variables.set('JPJVERSION', '=', ['0.1.0'])

        for name in os.environ:
            if name[-4:] == 'PATH':
                value = os.environ[name].split(':')
            else:
                value = [ os.environ[name] ]
            variables.set(name, '=', value)

        self.variable_stack = [ (Variables('local'), True), (variables, True) ]

    def open_scope(self, tag, variables = None):
        if variables == None:
            self.variable_stack.insert(0, (Variables(tag), True))
        else:
            self.variable_stack.insert(0, (variables, False))

    def close_scope(self):
        self.variable_stack.pop(0)

    def add_local(self, names, value):
        for (variables, writable) in self.variable_stack:
            if writable:
                break
        for name in names:
            variables.set(name, '=', value)

    def set(self, names, operation, value):
        for name in names:
            for (variables, writable) in self.variable_stack:
                if writable and (name in variables):
                    break
            variables.set(name, operation, value)

    def get(self, name):
        value = None
        for (variables, writable) in self.variable_stack:
            value = variables.get(name)
            if value != None:
                break
        else:
            value = []
        return value

    def dump(self, exclude = ['global']):
        for (variables, writable) in reversed(self.variable_stack):
            variables.dump(writable, exclude)

import fnmatch
import re

import jam.condition
import jam.exceptions
import jam.token

class Lines:
    """Base class for tokenised line iterators."""

    def __init__(self, lines, tag = 'Lines'):
        self.lines = lines
        self.iterator = None
        self.context = {}
        self.tag = tag

    def __iter__(self):
        self.iterator = iter(self.lines)
        return self

    def __next__(self):
        return next(self.iterator)

    def interrupt(self, name, arguments):
        raise jam.exceptions.JamInterrupt(name, arguments)

    def __setitem__(self, key, value):
        self.context[key] = value

    def __getitem__(self, key):
        if key in self.context:
            return self.context[key]
        return None

class Jamfile(Lines):
    """Reads a Jamfile, tokenizes it and organises the tokens into lines."""

    def __init__(self, path, tag = 'Jamfile'):
        lines = []
        line = jam.token.TokenList()
        t = ''
        line_number = 0
        counter = re.compile(r'\\\\|\\"|"')
        tokenize = re.compile(r'(?P<token>(?P<quote>")?(?(quote)(?:\\\\|\\"|[^"])*"|(?:\\\\|\\"|\\\s|[^"\s])+))(?P<white>\s*)')
        quoted_replace = re.compile(r'\\["\\]')
        unquoted_replace = re.compile(r'\\["\\\s]')
        def replace(match_object):
            return match_object.group(0)[1:]
        with open(path, mode='r', encoding='utf-8') as f:
            for text in f:
                line_number +=1
                try:
                    while counter.findall(text).count('"') & 1:
                        text += next(f)
                        line_number += 1
                except StopIteration:
                    raise jam.exceptions.JamSyntaxError(text)
                token_iterator = tokenize.finditer(text)
                for m in token_iterator:
                    if m.group('quote'):
                        t += quoted_replace.sub(replace, m.group('token')[1:-1])
                    else:
                        t += unquoted_replace.sub(replace, m.group('token'))
                    w = m.group('white')
                    if w:
                        if t and (t[0] == '#'):
                            t = ''
                            break
                        line.append(t, trailing_whitespace = w, filename = path, line_number = line_number)
                        if t in (';', '{', '}'):
                            lines.append(line)
                            line = jam.token.TokenList()
                        t = ''
        if t:
            line.append(t, trailing_whitespace = '', filename = path, line_number = line_number)
        if line:
            lines.append(line)
        Lines.__init__(self, lines, tag)

class Scope(Lines):
    def __init__(self, lines, variable_stack, tag = 'Scope'):
        Lines.__init__(self, lines, tag)
        self.variable_stack = variable_stack

    def __iter__(self):
        self.variable_stack.open_scope(self.tag)
        return Lines.__iter__(self)

    def end(self):
        self.variable_stack.close_scope()
        raise StopIteration

    def __next__(self):
        try:
            line = Lines.__next__(self)
        except StopIteration:
            self.end()
        return line

    def interrupt(self, name, arguments):
        self.variable_stack.close_scope()
        Lines.interrupt(self, name, arguments)

class Switch(Scope):
    def __init__(self, value, lines, variable_stack, tag = 'Switch'):
        valid = False
        case = []
        for line in lines:
            if (line[0] == 'case') and (line[2] == ':'):
                if valid:
                    break
                if any(fnmatch.fnmatch(i, line[1]) for i in value):
                    valid = True
                    case.append(line[3:])
            elif valid:
                case.append(line)
        Scope.__init__(self, case, variable_stack, tag)

class Loop(Scope):
    """Base class for tokenised line loop iterators."""

    def __init__(self, lines, variable_stack, tag = 'Loop'):
        Scope.__init__(self, lines, variable_stack, tag)
        self.stop = False

    def do_not_restart(self):
        return (self.iterator != None)

    def __iter__(self):
        self.stop = self.do_not_restart()
        return Scope.__iter__(self)

    def __next__(self):
        if self.stop:
            self.end()
        try:
            line = Scope.__next__(self)
        except StopIteration:
            if self.do_not_restart():
                raise StopIteration
            Scope.__iter__(self)
            line = Scope.__next__(self)
        return line

    def interrupt(self, name, arguments):
        caught = False
        if not values:
            if name == 'break':
                self.stop = True
                caught = True
            elif name == 'continue':
                if self.do_not_restart():
                    self.stop = True
                else:
                    self.iterator = iter(self.lines)
                caught = True
        if not caught:
            Scope.interrupt(self, name, arguments)
        

class ForLoop(Loop):
    def __init__(self, variable_name, values, lines, variable_stack, tag = 'For Loop'):
        Loop.__init__(self, lines, variable_stack, tag)
        self.variable_name = variable_name
        self.values_iterator = iter(values)

    def do_not_restart(self):
        try:
            self.variable_stack.set([ self.variable_name ], '=', [ next(self.values_iterator) ])
        except StopIteration:
            return True
        return False

class WhileLoop(Loop):
    def __init__(self, condition, lines, variable_stack, target_tree, rules, tag = 'While Loop'):
        Loop.__init__(self, lines, variable_stack, tag)
        self.condition = jam.condition.Condition(condition)
        self.target_tree = target_tree
        self.rules = rules

    def do_not_restart(self):
        return not self.condition(self.variable_stack, self.target_tree, self.rules)

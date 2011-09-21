"""
token.py
part of 'JPJ is Python Jam'
Copyright (C) 2011 Jonathan James
See README for license
--------------------------------------------------------------------------------
"""

import re

import jam.exceptions
import jam.path
import jam.sequence

class Token(str):
    def __new__(cls, arg, **args):
        if isinstance(arg, list):
            arg = ''.join(arg)
        return str.__new__(cls, arg)

    def __init__(self, arg, **args):
        metadata = ('trailing_whitespace', 'filename', 'line_number')
        try:
            t = args['token']
            for m in metadata:
                try:
                    a = getattr(t, m)
                except AttributeError:
                    a = None
                setattr(self, m, a)
        except KeyError:
            for m in metadata:
                try:
                    a = args[m]
                except:
                    a = None
                setattr(self, m, a)
        str.__init__(self)

    def variable_substitutions(self, variables):
        sub_tokenize = re.compile(r'(\$\(|\)|\[|\]|:[BDEGJLMPSU]*?[BDEGJMRS]=|:[BDEGJLMPSU]+)')
        sub_tokens = jam.sequence.JamList(sub_tokenize.split(self))
        sub_tokens_list = [ sub_tokens ]
        expanded_sub_tokens_list = []
        token_list = TokenList()
        whitespace = self.trailing_whitespace
        self.trailing_whitespace = ' '
        while sub_tokens_list:
            for sub_tokens in sub_tokens_list:
                pair = sub_tokens.innermost_enclosed_sequence('$(', ')', 1, len(sub_tokens), 2)
                if pair == None:
                    token_list.append(sub_tokens, token = self)
                    continue
                (left, right) = pair
                value = variables.get(sub_tokens[left + 1])
                if (right - left) > 2:
                    in_range = False
                    jam_path = jam.path.JamPath()
                    for index in range(left + 2, right, 2):
                        if sub_tokens[index] == ']':
                            if (not in_range) or sub_tokens[index + 1]:
                                raise jam.exceptions.JamSyntaxError
                            in_range = False
                        elif sub_tokens[index] == '[':
                            in_range = True
                            r = sub_tokens[index + 1].partition('-')
                            if not r[0].isdigit():
                                raise jam.exceptions.JamSyntaxError
                            if not r[1]:
                                value = value[int(r[0]) - 1:int(r[0])]
                            elif not r[2]:
                                value = value[int(r[0]) - 1:]
                            elif r[2].isdigit():
                                value = value[int(r[0]) - 1:int(r[2])]
                            else:
                                raise jam.exceptions.JamSyntaxError
                        elif sub_tokens[index][0] == ':':
                            if sub_tokens[index][-1] == '=':
                                jam_path[sub_tokens[index][-2]] = sub_tokens[index + 1]
                                sub_tokens[index] = sub_tokens[index][0:-2]
                            if len(sub_tokens[index]) > 1:
                                for c in sub_tokens[index][1:]:
                                    jam_path[c] = None
                    if in_range:
                        raise jam.exceptions.JamSyntaxError
                    value = jam_path(value)
                expanded_sub_tokens_list.extend([ sub_tokens[:left - 1] + [ sub_tokens[left - 1] + str(t) + sub_tokens[right + 1] ] + sub_tokens[right + 2:] for t in value ])
            sub_tokens_list = expanded_sub_tokens_list
            expanded_sub_tokens_list = []
        self.trailing_whitespace = whitespace
        if token_list:
            token_list[-1].trailing_whitespace = whitespace
        return token_list

@jam.sequence.jam_sequence('__add__', '__mul__', '__radd__', '__rmul__')
class TokenList(list):

    def _make_token(arg, **args):
        if isinstance(arg, Token):
            token = arg
        else:
            token = Token(arg, **args)
        return token

    def append(self, arg, **args):
        list.append(self, TokenList._make_token(arg, **args))

    def insert(self, index, arg, **args):
        list.insert(self, index, TokenList._make_token(arg, **args))

    def extend(self, arg):
        if isinstance(arg, TokenList):
            list.extend(self, arg)
        else:
            list.extend(self, [ TokenList._make_token(t) for t in arg ])

    def variable_substitutions(self, variables, *range_parameters):
        token_list = TokenList()
        if range_parameters == ():
            range_parameters = (0, len(self), 1)
        for i in range(*range_parameters):
            t = self[i]
            if not isinstance(t, Token):
                raise jam.exceptions.JamSyntaxError
            token_list.extend(t.variable_substitutions(variables))
        return token_list

    def test_variable_substitutions(self, variables, *range_parameters):
        if range_parameters == ():
            range_parameters = (0, len(self), 1)
        for i in range(*range_parameters):
            t = self[i]
            if not isinstance(t, Token):
                raise jam.exceptions.JamSyntaxError
            if any(t.variable_substitutions(variables)):
                return True
        return False

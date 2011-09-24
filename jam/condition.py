"""
condition.py
part of 'JPJ is Python Jam'
Copyright (C) 2011 Jonathan James
See README for license
--------------------------------------------------------------------------------
"""

import jam.exceptions
import jam.parse

class Condition:
    def __init__(self, condition):
        self.condition = condition

    def __call__(self, variable_stack, target_tree, rules):
        working = jam.parse.expand_rules(self.condition, variable_stack, target_tree, rules)
        working.insert(0, '(')
        working.append(')')
        while working:
            (left, right) = working.innermost_enclosed_sequence('(', ')')
            compare = -1
            negate = False
            value = False
            operation = '||'
            l = left + 1
            for index in range(left + 1, right + 1):
                if (index == right) or (working[index] in ('&&', '||')):
                    v = False
                    if compare == -1:
                        if ((index - l) == 1) and isinstance(working[l], bool):
                            v = working[l]
                        else:
                            v = working.test_variable_substitutions(variable_stack, l, index)
                    else:
                        one = working.variable_substitutions(variable_stack, l, compare)
                        two = working.variable_substitutions(variable_stack, compare + 1, index)
                        if working[compare] == '=':
                            v = (one == two)
                        elif working[compare] == '!=':
                            v = (one != two)
                        elif working[compare] == '<':
                            v = (one < two)
                        elif working[compare] == '<=':
                            v = (one <= two)
                        elif working[compare] == '>':
                            v = (one > two)
                        elif working[compare] == '>=':
                            v = (one >= two)
                        else:
                            v = set(one).issubset(set(two))
                        compare = -1
                    if negate:
                        v = not v
                    if operation == '&&':
                        value = value and v
                    else:
                        value = value or v
                    if index < right:
                        operation = working[index]
                        l = index + 1
                elif working[index] == '!':
                    if index == l:
                        negate = not negate
                        l += 1
                    else:
                        raise jam.exceptions.JamSyntaxError
                elif working[index] in ('=', '!=', '<', '<=', '>', '>=', 'in'):
                    if compare != -1:
                        raise jam.exceptions.JamSyntaxError
                    compare = index
            working[right] = value
            del working[left:right]
            if len(working) <= 1:
                break
        return working and working[0]

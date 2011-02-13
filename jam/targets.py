import re
import subprocess

import jam.exceptions
import jam.path
import jam.variables

class Target:
    def __init__(self, key):
        self.key = key
        self.dependancy_list = []
        self.included_list   = []
        self.actions_list = []
        self.variables = jam.variables.Variables(key)
        self.always = False
        self.leaves = False
        self.no_care = False
        self.not_file = False
        self.no_update = False
        self.temporary = False
        self.bind_result = None
        self.built = False
        self.updated = False
        self.exists = False

    def __bool__(self):
        return (self.bind_result != [])

    def depends(self, target):
        if target not in self.dependancy_list:
            self.dependancy_list.append(target)

    def includes(self, target):
        if target not in self.included_list:
            self.included_list.append(target)

    def set(self, names, operation, value):
        for name in names:
            self.variables.set(name, operation, value)

    def actions(self, actions, arguments):
        separate = True
        if actions[1]['together']:
            for a in self.actions_list:
                if (a[0][3] == actions[3]) and (a[1][0] == arguments[0]) and (a[1][2:] == arguments[2:]):
                    a[1][1].extend(arguments[1])
                    separate = False
                    break
        if separate:
            self.actions_list.append((actions, arguments))

    def find(self, stat):
        location = jam.path.splitgrist(self.key)[1]
        exists = False
        locate = self.variables.get('LOCATE')
        if locate:
            jam_path       = jam.path.JamPath(R = locate[0])
            bound_location = jam_path([location])[0]
            exists         = stat.exists(bound_location)
        else:
            search = self.variables.get('SEARCH')
            for root in search:
                jam_path       = jam.path.JamPath(R = root)
                bound_location = jam_path([location])[0]
                exists         = stat.exists(bound_location)
                if exists:
                    break
            else:
                bound_location = location
                exists         = stat.exists(bound_location)
        return (bound_location, exists)

    def bind(self, rebuild, variable_stack, rule_dictionary, stat, parent_timestamp, keep, debug_dependancies):
        bind_result = self.bind_result
        if bind_result == None:
            (location, exists) = self.find(stat)
            timestamp = None
            if exists and (not self.no_update):
                timestamp = stat.timestamp(location)

            location = jam.path.splitgrist(self.key)[1]
            dirty = self.always or rebuild
            timestamp = None
            if not self.not_file:
                if stat.exists(location):
                    if not self.no_update:
                        timestamp = stat.timestamp(location)
                    self.exists = True
                else:
                    search = self.variables.get('SEARCH')
                    locate = self.variables.get('LOCATE')
                    bound_location = ''
                    if search:
                        for root in search:
                            jam_path = jam.path.JamPath(R = root)
                            bound_location = jam_path([ location ])[0]
                            if stat.exists(bound_location):
                                timestamp = stat.timestamp(bound_location)
                                dirty = False
                                self.exists = True
                                break
                            bound_location = ''
                    elif locate:
                        jam_path = jam.path.JamPath(R = locate[0])
                        bound_location = jam_path([ location ])[0]
                        if stat.exists(bound_location):
                            if not self.no_update:
                                timestamp = stat.timestamp(bound_location)
                            self.exists = True
                        elif self.temporary:
                            timestamp = parent_timestamp
                            if timestamp == None:
                                dirty = True
                        else:
                            dirty = True
                    if not bound_location and (not self.no_care):
                        raise jam.exceptions.JamBindError(self.key)
                    location = bound_location

                hdrscan = self.variables.get('HDRSCAN')
                hdrrule = self.variables.get('HDRRULE')
                if location and hdrscan and hdrrule and variable_stack and rule_dictionary:
                    arguments = [[self.key], []]
                    regexs = [re.compile(r) for r in hdrscan]
                    with open(location) as f:
                        variable_stack.open_scope('hdrscan', self.variables)
                        for line in f:
                            for regex in regexs:
                                m = regex.match(line)
                                if m:
                                    arguments[1] = list(m.groups())
                                    rule_dictionary(hdrrule, arguments)
                        variable_stack.close_scope()

            for depends in self.dependancy_list:
                if debug_dependancies:
                    print('Depends "'+self.key+'" : "'+depends.key+'"')
                for triple in depends.bind(rebuild, variable_stack, rule_dictionary, stat, timestamp, keep, debug_dependancies):
                    if triple[1] or ((timestamp != None) and (triple[2] != None) and (timestamp < triple[2])):
                        print(location, 'is dirty due to', triple[0], triple[1], timestamp, triple[2]) 
                        dirty = True
                        break

            bind_result =[(location, dirty, timestamp)]

            for included in self.included_list:
                if debug_dependancies:
                    print('Includes "'+self.key+'" : "'+included.key+'"')
                bind_result.extend(included.bind(rebuild, variable_stack, rule_dictionary, stat, None, keep, debug_dependancies))

            if keep:
                self.bind_result = bind_result
                self.built = not dirty

        return bind_result

    def build(self, variable_stack, target_tree):
        if not self.built:
            for depends in self.dependancy_list:
                depends.build(variable_stack, target_tree)
            for included in self.included_list:
                included.build(variable_stack, target_tree)
            variable_stack.open_scope('build', self.variables)
            for action in self.actions_list:
                variable_stack.open_scope(self.key)
                arguments = action[1]
                for i in range(0, len(arguments)):
                    variable = [str(i + 1)]
                    if (i == 1) and action[0][1]['updated']:
                        value = []
                        for a in arguments[1]:
                            t = target_tree[a]
                            if t.updated:
                                value.append(t.bind_result[0][0])
                        variable_stack.add_local(variable, value)
                    elif (i == 1) and action[0][1]['existing']:
                        value = []
                        for a in arguments[1]:
                            t = target_tree[a]
                            if t.exists:
                                value.append(t.bind_result[0][0])
                        variable_stack.add_local(variable, value)
                    elif i < 2:
                        variable_stack.add_local(variable, [target_tree[a].bind_result[0][0] for a in arguments[i]])
                    else:
                        variable_stack.add_local(variable, arguments[i])
                bound = action[0][0]
                for b in bound:
                    variable_stack.add_local([b], [target_tree[a].bind_result[0][0] for a in variable_stack.get(b)])
                text = []
                for t in action[0][2].variable_substitutions(variable_stack):
                    if t:
                        text.append(str(t))
                        if t.trailing_whitespace:
                            text.append(t.trailing_whitespace)
                        else:
                            text.append(' ')
                command = ''.join(text)
                failed = (subprocess.call(command, shell = True) != 0)
                variable_stack.close_scope()
            variable_stack.close_scope()
            self.built = True
            self.updated = True
            self.exists = True

    def dump(self, name, show_variables):
        print(name,self.bind_result)
        if show_variables:
            self.variables.dump(True, [])
            print()


class TargetTree(dict):
    def __init__(self):
        dict.__init__(self)
        self.stat = jam.path.JamStat()

    def __missing__(self, nonexsistent_key):
        target = Target(nonexsistent_key)
        self[nonexsistent_key] = target
        return target

    def count(self):
        count = 0
        updating = 0
        for target in self:
            t = self[target]
            if t:
                count += 1
                if (not t.built) and t.actions_list:
                    updating += 1
        return (count, updating)

    def depends(self, targets, sources):
        for target in targets:
            for source in sources:
                self[target].depends(self[source])

    def includes(self, targets, sources):
        for target in targets:
            for source in sources:
                self[target].includes(self[source])

    def always(self, targets):
        for target in targets:
            self[target].always = True

    def leaves(self, targets):
        for target in targets:
            self[target].leaves = True

    def no_care(self, targets):
        for target in targets:
            self[target].no_care = True

    def not_file(self, targets):
        for target in targets:
            self[target].not_file = True

    def no_update(self, targets):
        for target in targets:
            self[target].no_update = True

    def temporary(self, targets):
        for target in targets:
            self[target].temporary = True

    def set(self, targets, names, operation, value):
        for target in targets:
            self[target].set(names, operation, value)

    def actions(self, actions, arguments):
        for target in arguments[0]:
            self[target].actions(actions, arguments)

    def bind(self, target_map, variable_stack, rule_dictionary, debug_dependancies):
        for target in target_map:
            if target in self:
                self[target].bind(target_map[target], variable_stack, rule_dictionary, self.stat, None, True, debug_dependancies)
            else:
                print('don\'t know how to make '+target)

    def build(self, target_map, variable_stack):
        for target in target_map:
            if target in self:
                self[target].build(variable_stack, self)

    def include(self, name):
        if len(name) > 1:
            raise jam.exceptions.JamSyntaxError
        triple = self[name[0]].bind(True, None, None, self.stat, None, False, False)
        return triple[0][0]

    def on(self, name):
        if len(name) > 1:
            raise jam.exceptions.JamSyntaxError
        return self[name[0]].variables

    def dump(self, show_variables):
        for target in self:
            self[target].dump(target, show_variables)

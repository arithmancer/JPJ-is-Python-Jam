import re
import subprocess
import time

import jam.exceptions
import jam.path
import jam.variables

class BuildTarget:
    def __init__(self, location, dirty, timestamp):
        self.location        = location
        self.dirty           = dirty
        self.timestamp       = timestamp
        self.dependancy_list = []

    def extend(self, dependancy_list):
        self.dependancy_list.extend(dependancy_list)

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
        self.binding = False
        self.built = False
        self.attempted = False
        self.updated = False
        self.exists = False
        self.failed = False

    def __bool__(self):
        return (self.bind_result != None)

    def depends(self, target):
        if target not in self.dependancy_list:
            self.dependancy_list.append(target)

    def includes(self, target):
        if target not in self.included_list:
            self.included_list.append(target)

    def set(self, names, operation, value):
        for name in names:
            self.variables.set(name, operation, value)

    def actions(self, name, actions, arguments):
        separate = True
        if actions[1]['together']:
            for a in self.actions_list:
                if (a[0][3] == actions[3]) and (a[1][0] == arguments[0]) and (a[1][2:] == arguments[2:]):
                    a[1][1].extend(arguments[1])
                    separate = False
                    break
        if separate:
            self.actions_list.append((actions, arguments, name))

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
            if search == None:
                search = []
            for root in search:
                jam_path       = jam.path.JamPath(R = root)
                bound_location = jam_path([location])[0]
                exists         = stat.exists(bound_location)
                if exists:
                    break
            else:
                bound_location = location
                exists         = stat.exists(bound_location)
        if (not exists) and (not self.actions_list) and (not self.no_care) and (not jam.path.splitmodule(bound_location)[1]):
            print(bound_location+':', 'No such file or directory')
        return (bound_location, exists)


    def bind(self, rebuild, variable_stack, rule_dictionary, stat, parent_timestamp, debug_options, level):
        if self.binding:
            print('warning:', self.key, 'depends on itself')
            return []
        bind_result = self.bind_result
        if bind_result == None:
            if debug_options['make tree']:
                print('make\t--\t', ' '*level, self.key)
            self.binding = True
            dirty = self.always or rebuild
            timestamp = None
            if self.not_file:
                location = self.key
                exists = False
            else:
                (location, exists) = self.find(stat)
                if exists:
                    timestamp = stat.timestamp(location)
                else:
                    if self.temporary:
                        timestamp = parent_timestamp
                        if timestamp == None:
                            dirty = True
                    elif (self.actions_list) and (not self.no_care):
                        dirty = True

                if debug_options['make tree']:
                    if location != self.key:
                        print('bind\t--\t', ' '*level, self.key, ':', location)
                    if timestamp:
                        if exists:
                            print('time\t--\t', ' '*level, self.key, ':', time.strftime('%a %b %d %H:%M:%S %Y', time.gmtime(timestamp)))
                        else:
                            print('time\t--\t', ' '*level, self.key, ':', 'parents')

                hdrscan = self.variables.get('HDRSCAN')
                hdrrule = self.variables.get('HDRRULE')
                if exists and hdrscan and hdrrule and variable_stack and rule_dictionary:
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

            test_timestamp = None
            if not self.no_update:
                test_timestamp = timestamp

            newer = []
            for depends in self.dependancy_list:
                if debug_options['dependancies']:
                    print('Depends "'+self.key+'" : "'+depends.key+'"')
                for target in depends.bind(rebuild, variable_stack, rule_dictionary, stat, timestamp, debug_options, level + 1):
                    if target.dirty or ((test_timestamp != None) and (target.timestamp != None) and (timestamp < target.timestamp)):
                        if target.dirty:
                            newer.append(target.location+'*')
                        else:
                            newer.append(target.location)
                        dirty = True
                        break

            bind_result =[BuildTarget(location, dirty, test_timestamp)]

            for included in self.included_list:
                if debug_options['dependancies']:
                    print('Includes "'+self.key+'" : "'+included.key+'"')
                bind_result.extend(included.bind(rebuild, variable_stack, rule_dictionary, stat, parent_timestamp, debug_options, level + 1))

            self.bind_result = bind_result
            self.binding = False
            self.exists = exists
            self.built = not dirty

            if debug_options['make tree']:
                flag = ' '
                if (not self.not_file) and dirty:
                    flag = '+'
                elif exists and (parent_timestamp != None) and (test_timestamp != None) and (parent_timestamp < test_timestamp):
                    flag = '*'
                print('made'+flag+'\t--\t', ' '*level, self.key)

            if (not self.not_file) and dirty and debug_options['causes']:
                cause = ''
                if timestamp == None:
                    # (timestamp == None) rather than (not exists) so that temporary targets aren't reported as missing
                    cause = 'was missing'
                elif rebuild:
                    cause = 'was touched'
                elif self.always:
                    cause = 'is always rebuilt'
                else:
                    cause = 'was older than ' + ', '.join(newer)
                print(self.key, cause)

        if parent_timestamp != None:
            for target in bind_result:
                if (target.timestamp != None) and (parent_timestamp < target.timestamp):
                    self.updated = True

        return bind_result

    def build(self, variable_stack, target_tree, output_file, debug_options):
        if (not self.built) and (not self.attempted):
            self.attempted = True
            failed = False
            for depends in self.dependancy_list:
                if not depends.build(variable_stack, target_tree, output_file, debug_options):
                    failed = True
                    if self.actions_list:
                        print('...skipped', self.bind_result[0].location, 'for lack of', depends.bind_result[0].location)
            for included in self.included_list:
                included.build(variable_stack, target_tree, output_file, debug_options)
            if failed:
                return False
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
                                value.append(t.bind_result[0].location)
                        variable_stack.add_local(variable, value)
                    elif (i == 1) and action[0][1]['existing']:
                        value = []
                        for a in arguments[1]:
                            t = target_tree[a]
                            if t.exists:
                                value.append(t.bind_result[0].location)
                        variable_stack.add_local(variable, value)
                    elif i < 2:
                        variable_stack.add_local(variable, [target_tree[a].bind_result[0].location for a in arguments[i]])
                    else:
                        variable_stack.add_local(variable, arguments[i])
                bound = action[0][0]
                for b in bound:
                    variable_stack.add_local([b], [target_tree[a].bind_result[0].location for a in variable_stack.get(b)])
                text = []
                for t in action[0][2].variable_substitutions(variable_stack):
                    if t:
                        text.append(str(t))
                        if t.trailing_whitespace:
                            text.append(t.trailing_whitespace)
                        else:
                            text.append(' ')
                command = ''.join(text)
                if (debug_options['actions'] and (not action[0][1]['quietly'])) or (debug_options['quiet'] and action[0][1]['quietly']):
                    print(action[2], *action[1][0])
                if debug_options['shell']:
                    print(command)
                if output_file:
                    output_file.write(command)
                elif not debug_options['noupdate']:
                    failed = (subprocess.call(command, shell = True) != 0)
                    if failed and debug_options['quick']:
                        raise jam.exceptions.JamQuickExit
                variable_stack.close_scope()
                if failed:
                    print('\n', command)
                    print('...failed', action[2], *action[1][0])
                    break
                else:
                    self.updated = True
            variable_stack.close_scope()
            if failed:
                self.failed = True
            else:
                self.built = True
                self.exists = True

        return self.built

    def dump(self, name, show_variables):
        print(name,self.bind_result)
        if show_variables:
            self.variables.dump(True, [])


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
        temporary = 0
        updated = 0
        failed = 0
        for target in self:
            t = self[target]
            if t:
                count += 1
                if t.failed:
                    failed += 1
                elif (not t.built) and t.actions_list:
                    updating += 1
                if t.exists and t.temporary:
                    temporary += 1
                if t.updated:
                    updated += 1
        return (count, updating, temporary, updated, failed)

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

    def actions(self, name, actions, arguments):
        for target in arguments[0]:
            self[target].actions(name, actions, arguments)

    def bind(self, target_map, variable_stack, rule_dictionary, debug_options):
        for target in target_map:
            if target in self:
                self[target].bind(target_map[target], variable_stack, rule_dictionary, self.stat, None, debug_options, 0)
            else:
                print('don\'t know how to make '+target)

    def build(self, target_map, variable_stack, output_file, debug_options):
        for target in target_map:
            if target in self:
                self[target].build(variable_stack, self, output_file, debug_options)

    def include(self, name):
        if len(name) > 1:
            raise jam.exceptions.JamSyntaxError
        return self[name[0]].find(self.stat)

    def on(self, name):
        if len(name) > 1:
            raise jam.exceptions.JamSyntaxError
        return self[name[0]].variables

    def dump(self, show_variables):
        for target in self:
            self[target].dump(target, show_variables)

import os.path
import sys

import jam.variables
import jam.targets
import jam.lines
import jam.parse
import jam.rules
import jam.exceptions

def main():
    arguments = sys.argv[1:]
    target_map = {}
    options = {'a': False, 'g': False, 'h': False, 'n': False, 'q': False, 'v': False}
    parameters = {'d': [], 'f': [], 'j': [], 'o': [], 's': [], 't': []}
    try:
        while arguments:
            arg = arguments.pop(0)
            if arg[0] == '-':
                c = None
                for i in range(1, len(arg)):
                    c = arg[i]
                    if c in options:
                        options[c] = True
                        c = None
                    elif c in parameters:
                        break
                    else:
                        raise JamOptionError(c)
                if c != None:
                    if arg[(i + 1):]:
                        parameters[c].append(arg[(i + 1):])
                    elif arguments:
                        parameters[c].append(arguments.pop(0))
                    else:
                        raise JamOptionError(c)
            else:
                target_map[arg] = False
    except exceptions.JamOptionError as option_error:
        if option_error.option in parameters:
            print('option: -'+option_error.option+' needs argument\n')
        else:
            print('Invalid option: -'+option_error.option+'\n')
        options['v'] = False
        options['h'] = True
    if not target_map:
        target_map['all'] = False
    try:
        debug = {'a': False, 'c': False, 'd': False, 'm': False, 'p': False, 'x': False}
        for d in ''.join(parameters['d']):
            if d in debug:
                debug[d] = True
            else:
                print('Invalid debug flag \''+d+'\'.')

        if options['v']:
            raise exceptions.JamUserExit('PJam - based on FT-Jam 2.5.2.')
        if options['h']:
            raise exceptions.JamUserExit('\n'
                                         'usage: jam [ options ] targets...\n\n'
                                         '-a      Build all targets, even if they are current.\n'
                                         '-dx     Display (a)actions (c)causes (d)dependencies\n'
                                         '(m)make tree (x)commands (0-9) debug levels.\n'
                                         '-fx     Read x instead of Jambase.\n'
                                         '-g      Build from newest sources first.\n'
                                         '-jx     Run up to x shell commands concurrently.\n'
                                         '-n      Don\'t actually execute the updating actions.\n'
                                         '-ox     Write the updating actions to file x.\n'
                                         '-q      Quit quickly as soon as a target fails.\n'
                                         '-sx=y   Set variable x=y, overriding environment.\n'
                                         '-tx     Rebuild x, even if it is up-to-date.\n'
                                         '-v      Print the version of jam and exit.\n')

        variable_stack = jam.variables.VariableStack()
        for s in parameters['s']:
            t = s.partition('=')
            variable_stack.set(t[0:1], '=', t[2:3])

        for t in parameters['t']:
            target_map[t] = True

        if options['a']:
            for t in target_map:
                target_map[t] = True

        if not parameters['f']:
            jambase = os.path.join(sys.path[0],'jam/Jambase')
            print(jambase)
            parameters['f'].append(jambase)

        target_tree = jam.targets.TargetTree()
        rule_dictionary = jam.rules.Rules(target_tree, variable_stack, debug['p'])

        for jambase in parameters['f']:
            jam.parse.parse(lines.Jamfile(jambase), variable_stack, target_tree, rule_dictionary)

        target_tree.bind(target_map, variable_stack, rule_dictionary, debug['d'])
        (count, updating, updated) = target_tree.count()
        print('...found', count, 'target(s)...')
        if updating:
            print('...updating', updating, 'target(s)...')
        target_tree.bind({'all': False}, None, None, False)
        target_tree.build(target_map, variable_stack)
        (count, updating, updated) = target_tree.count()
        if updated:
            print('...updated', updated, 'target(s)...')

    except jam.exceptions.JamUserExit as jam_exit:
        print(*jam_exit.message)
    except jam.exceptions.JamUnknownRule as jam_rule:
        print('Unknown Rule:', jam_rule.name)
    except jam.exceptions.JamBindError as bind_error:
        print('Bind Error:', bind_error.target)
    except Exception as exception:
        variable_stack.dump([])
        raise exception

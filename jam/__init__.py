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
        debug = []
        for d in ''.join(parameters['d']):
            if d in ('a', 'c', 'd', 'm', 'p', 'x'):
                debug.append(d)
            else:
                print('Invalid debug flag \''+d+'\'.')

        debug_options = {'summary'      : False,
                         'actions'      : False,
                         'quiet'        : False,
                         'temporary'    : False,
                         'shell'        : False,
                         'dependancies' : False,
                         'make tree'    : False,
                         'pjam'         : False,
                         'noupdate'     : False,
                         'quick'        : False}

        if options['n']:
            debug_options['noupdate'] = True
            debug.extend(['a','x'])

        if debug:
            if 'a' in debug:
                debug_options['summary']      = True
                debug_options['actions']      = True
                debug_options['quiet']        = True
                debug_options['temporary']    = True
            if 'd' in debug:
                debug_options['dependancies'] = True
            if 'm' in debug:
                debug_options['make tree']    = True
            if 'p' in debug:
                debug_options['pjam']         = True
            if 'x' in debug:
                debug_options['shell']        = True
        else:
            debug_options['summary']   = True
            debug_options['actions']   = True

        if options['q']:
            debug_options['quick'] = True

        if options['v']:
            raise exceptions.JamUserExit('JPJ: JPJ is Python Jam - based on FT-Jam 2.5.2.')
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
        rule_dictionary = jam.rules.Rules(target_tree, variable_stack, debug_options)

        for jambase in parameters['f']:
            jam.parse.parse(lines.Jamfile(jambase), variable_stack, target_tree, rule_dictionary)

        target_tree.bind(target_map, variable_stack, rule_dictionary, debug_options)

        (count, updating, temporary, newer, failed) = target_tree.count()
        if debug_options['summary']:
            print('...found', count, 'target(s)...')
        if debug_options['temporary'] and temporary:
            print('...using', temporary, 'temp target(s)...')
        if debug_options['summary'] and updating:
            print('...updating', updating, 'target(s)...')

        debug_options['dependancies'] = False
        debug_options['make tree']    = False
        target_tree.bind({'all': False}, None, None, debug_options)

        output_file = None
        if parameters['o']:
            output_file = open(parameters['o'][0], mode='w', encoding='utf-8')
        target_tree.build(target_map, variable_stack, output_file, debug_options)
        if output_file:
            output_file.close()

        (count, skipped, temporary, updated, failed) = target_tree.count()
        updated -= newer
        if debug_options['summary']:
            if failed:
                print('...failed updating', failed, 'target(s)...')
            if skipped:
                print('...skipped', skipped, 'target(s)...')
            if updated:
                print('...updated', updated, 'target(s)...')

    except jam.exceptions.JamUserExit as jam_exit:
        print(*jam_exit.message)
    except jam.exceptions.JamQuickExit:
        pass
    except Exception as exception:
        variable_stack.dump([])
        raise exception

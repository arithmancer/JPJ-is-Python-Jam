import jam.condition
import jam.exceptions
import jam.lines

def get_block(block):
    if block == None:
        raise jam.exceptions.JamSyntaxError('{} inside []')
    indent = 1
    sub_block = []
    try:
        while indent > 0:
            line = next(block)
            if line[-1] == '{':
                indent +=1
            elif line[-1] == '}':
                indent -=1
            if indent == 0:
                if len(line) > 1:
                    sub_block.append(line[0:-1])
            else:
                sub_block.append(line)
    except StopIteration:
        raise jam.exceptions.JamSyntaxError
    return sub_block

def parse_line(line, block, variable_stack, target_tree, rules):
    if line[0] == 'else':
        if block == None:
            raise jam.exceptions.JamSyntaxError('else inside []')
        elif block['else'] == None:
            raise jam.exceptions.JamSyntaxError('else without corresponding if')
        elif block['else'] == False:
            if line[1] != 'if':
                block['else'] = None
            if line[-1] == '{':
                get_block(block)
            return []
        else:
            line = line[1:]
            block['else'] = None
    elif block != None:
        block['else'] = None

    on_target = False
    if line[0] == 'on':
        targets = None
        right = 1
        if line[1] == '[':
            pair = line.outermost_enclosed_sequence('[', ']')
            if pair != None:
                (left, right) = pair
                targets = expand_rules(line[left:right + 1], variable_stack, target_tree, rules)
        if targets == None:
            targets = line.variable_substitutions(variable_stack, 1, 2)
        variable_stack.open_scope('on', target_tree.on(targets)) 
        line = line[right + 1:]
        on_target = True

    if line[0] not in ('if', 'while'):
        line = expand_rules(line, variable_stack, target_tree, rules)

    result = []
    if block == None:
        line.append(';')
    length = len(line)
    if line[-1] == '{':
        sub_block = get_block(block)
        scope = None
        if length == 1:
            scope = jam.lines.Scope(sub_block, variable_stack)
        elif (length == 3) and (line[0] == 'rule'):
            rules.rule(line[1], sub_block)
        elif (length >= 3) and (line[0] == 'actions'):
            rules.actions(line[1:-1], sub_block)
        elif (length >= 3) and (line[0] == 'if'):
            if jam.condition.Condition(line[1:-1])(variable_stack, target_tree, rules):
                scope = jam.lines.Scope(sub_block, variable_stack, 'If')
                block['else'] = False
            else:
                block['else'] = True
        elif (length >= 3) and (line[0] == 'switch'):
            scope = jam.lines.Switch(line.variable_substitutions(variable_stack, 1, length - 1), sub_block, variable_stack)
        elif (length >= 3) and (line[0] == 'while'):
            scope = jam.lines.WhileLoop(line[1:-1], sub_block, variable_stack, target_tree, rules)
        elif (length >= 5) and (line[0] == 'for') and (line[2] == 'in'):
            variable_name = line[1].variable_substitutions(variable_stack)
            if len(variable_name) != 1:
                raise jam.exceptions.JamSyntaxError
            values = line.variable_substitutions(variable_stack, 3, length - 1)
            scope = jam.lines.ForLoop(variable_name[0], values, sub_block, variable_stack)
        else:
            raise jam.exceptions.JamSyntaxError
        if scope:
            try:
                parse(scope, variable_stack, target_tree, rules)
            except jam.exceptions.JamInterrupt as jam_interrupt:
                block.interrupt(jam_interrupt.name, jam_interrupt.values)
    elif line[-1] == ';':
        if block == None:
            line.pop(-1)
        if (length == 2) and (line[0] in ('break', 'continue')):
            block.interrupt(line[0], [])
        elif (length >= 2) and (line[0] == 'return'):
            block.interrupt('return', line.variable_substitutions(variable_stack, 1, length - 1))
        elif (length >= 3) and (line[0] == 'include'):
            (filename, exists) = target_tree.include(line.variable_substitutions(variable_stack, 1, length - 1))
            if exists:
                parse(jam.lines.Jamfile(filename), variable_stack, target_tree, rules)
        elif (length >= 3) and (line[0] == 'local'):
            if '=' in line:
                index = line.index('=')
                variable_names = line.variable_substitutions(variable_stack, 1, index)
                values = line.variable_substitutions(variable_stack, index + 1, length - 1)
            else:
                variable_names = line.variable_substitutions(variable_stack, 1, length - 1)
                values = []
            variable_stack.add_local(variable_names, values)
        else:
            operation = None
            on = None
            for index in range(0, length - 1):
                if line[index] == 'on':
                    on = index
                elif line[index] in ('=', '+=', '?=', 'default='):
                    operation = line[index]
                    if operation == 'default=':
                        operation = '?='
                    break
            if operation != None:
                values = line.variable_substitutions(variable_stack, index + 1, length - 1)
                if on == None:
                    variable_names = line.variable_substitutions(variable_stack, 0, index)
                    variable_stack.set(variable_names, operation, values)
                else:
                    variable_names = line.variable_substitutions(variable_stack, 0, on)
                    target_names = line.variable_substitutions(variable_stack, on + 1, index)
                    target_tree.set(target_names, variable_names, operation, values)
            else:
                rule_names = line[0].variable_substitutions(variable_stack)
                arguments = []
                start = 1
                try:
                    while start < (length - 1):
                        end = line.index(':', start)
                        arguments.append(line.variable_substitutions(variable_stack, start, end))
                        start = end + 1
                except ValueError:
                    arguments.append(line.variable_substitutions(variable_stack, start, length - 1))
                result = rules(rule_names, arguments)
    else:
        raise jam.exceptions.JamSyntaxError

    if on_target:
        variable_stack.close_scope()

    return result

def expand_rules(sequence, variable_stack, target_tree, rules):
    pair = sequence.innermost_enclosed_sequence('[', ']')
    if pair == None:
        return sequence[:]
    while pair != None:
        (left, right) = pair
        sequence = sequence[:left] + parse_line(sequence[left + 1:right], None, variable_stack, target_tree, rules) + sequence[right + 1:]
        pair = sequence.innermost_enclosed_sequence('[', ']')
    return sequence

def parse(block, variable_stack, target_tree, rules):
    try:
        for line in block:
            parse_line(line, block, variable_stack, target_tree, rules)
    #except jam.exceptions.JamSyntaxError as syntax:
    #    raise jam.exceptions.JamUserExit('Syntax Error in',line[0].filename,'on line',line[0].line_number,'\n', ' '.join(line))
    except jam.exceptions.JamInterrupt as jam_interrupt:
        raise jam_interrupt
    except Exception as exception:
        print(line)
        raise exception


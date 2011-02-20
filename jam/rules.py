import glob
import re

import jam.exceptions
import jam.lines
import jam.parse
import jam.path
import jam.token

class Rules:
   def __init__(self, target_tree, variable_stack, debug_rules):
      built_in_rules = {}
      built_in_rules['Depends']   = built_in_rules['DEPENDS']   = (2, target_tree.depends)
      built_in_rules['Includes']  = built_in_rules['INCLUDES']  = (2, target_tree.includes)
      built_in_rules['Always']    = built_in_rules['ALWAYS']    = (1, target_tree.always)
      built_in_rules['Leaves']    = built_in_rules['LEAVES']    = (1, target_tree.leaves)
      built_in_rules['NoCare']    = built_in_rules['NOCARE']    = (1, target_tree.no_care)
      built_in_rules['NotFile']   = built_in_rules['NOTFILE']   = (1, target_tree.not_file)
      built_in_rules['NoUpdate']  = built_in_rules['NOUPDATE']  = (1, target_tree.no_update)
      built_in_rules['Temporary'] = built_in_rules['TEMPORARY'] = (1, target_tree.temporary)
      built_in_rules['Echo'] = built_in_rules['ECHO'] = built_in_rules['echo'] = (1, self.echo)
      built_in_rules['Exit'] = built_in_rules['EXIT'] = built_in_rules['exit'] = (1, self.exit)
      built_in_rules['Glob'] = built_in_rules['GLOB'] = (2, self.glob)
      built_in_rules['Match'] = built_in_rules['MATCH'] = (2, self.match)
      if debug_rules:
         built_in_rules['PDumpVariables'] = (1, variable_stack.dump)
         built_in_rules['PDumpTargets'] = (0, target_tree.dump)
      self.built_in_rules = built_in_rules
      self.defined_rules = {}
      self.defined_actions = {}
      self.target_tree = target_tree
      self.variable_stack = variable_stack
      self.current_action_id = 0

   def echo(self, argument):
      print(*argument)

   def exit(self, argument):
      raise jam.exceptions.JamUserExit(argument)

   def glob(self, directories, patterns):
      result = jam.token.TokenList()
      for directory in directories:
         jam_path = jam.path.JamPath()
         jam_path['R'] = directory
         for pattern in jam_path(patterns):
            result.extend(glob.glob(pattern))
      return result

   def match(self, regexps, argument):
      result = jam.token.TokenList()
      for regexp in regexps:
         r = re.compile(regexp)
         for i in argument:
            for m in r.finditer(i):
               result.extend(jam.token.TokenList(m.groups()))
      return result

   def rule(self, name, block):
      self.defined_rules[name] = jam.lines.Lines(block)

   def actions(self, command, block):
      name = None
      modifier_dictionary = {'existing': False, 'ignore': False, 'piecemeal': False, 'quietly': False, 'together': False, 'updated': False}
      bound = None
      for token in command:
         if token == 'bind':
            if bound != None:
               raise jam.exceptions.JamSyntaxError('repeated modifier', token)
            bound = []
         elif token in modifier_dictionary:
            if modifier_dictionary[token]:
               raise jam.exceptions.JamSyntaxError('repeated modifier', token)
            modifier_dictionary[token] = True
         elif bound != None:
            bound.append(token)
         elif name != None:
            raise jam.exceptions.JamSyntaxError('unknown modifier', name, token)
         else:
            name = token
      if name == None:
         if bound:
            name = bound.pop(-1)
         else:
            raise jam.exceptions.JamSyntaxError('no action name')
      if bound == None:
         bound = []
      action = jam.token.TokenList()
      for line in block:
         action.extend(line)
      self.defined_actions[name] = (bound, modifier_dictionary, action, self.current_action_id)
      self.current_action_id += 1

   def __call__(self, rules, arguments):
      result = []
      for rule in rules:
         unknown_rule = True

         if rule in self.defined_actions:
            unknown_rule = False
            self.target_tree.actions(rule, self.defined_actions[rule], arguments)

         if rule in self.built_in_rules:
            unknown_rule = False
            f = self.built_in_rules[rule]
            r = None
            if len(arguments) <= f[0]:
               arguments.extend([[]]*(f[0] - len(arguments)))
               if f[0] == 0:
                  r = f[1]()
               if f[0] == 1:
                  r = f[1](arguments[0])
               elif f[0] == 2:
                  r = f[1](arguments[0], arguments[1])
               if r != None:
                  result.extend(r)
         elif rule in self.defined_rules:
            unknown_rule = False
            self.variable_stack.open_scope(rule)
            for i in range(0, len(arguments)):
               variable = [str(i + 1)]
               self.variable_stack.add_local(variable, arguments[i])
            try:
               jam.parse.parse(self.defined_rules[rule], self.variable_stack, self.target_tree, self)
            except jam.exceptions.JamInterrupt as jam_interrupt:
               if jam_interrupt.name == 'return':
                  result.extend(jam_interrupt.values)
               else:
                  raise jam.exceptions.JamSyntaxError
            self.variable_stack.close_scope()

         if unknown_rule:
            print('warning: unknown rule', rule)
      return result
       

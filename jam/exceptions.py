"""
exceptions.py
part of 'JPJ is Python Jam'
See README for license
--------------------------------------------------------------------------------
I'm not sure why the exceptions have their own file. They're just antisocial I
guess. 
"""

class JamSyntaxError(Exception):
    def __init__(self, *arguments):
        self.arguments = arguments

class JamOptionError(Exception):
    def __init__(self, option):
        self.option = option

class JamUserExit(Exception):
    def __init__(self, *message):
        self.message = message

class JamQuickExit(Exception):
    pass

class JamInterrupt(Exception):
    def __init__(self, name, arguments):
        self.name = name
        self.values = arguments

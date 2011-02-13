
class JamSyntaxError(Exception):
    def __init__(self, *arguments):
        self.arguments = arguments

class JamOptionError(Exception):
    def __init__(self, option):
        self.option = option

class JamBindError(Exception):
    def __init__(self, target):
        self.target = target

class JamUserExit(Exception):
    def __init__(self, *message):
        self.message = message

class JamUnknownRule(Exception):
    def __init__(self, name):
        self.name = name

class JamInterrupt(Exception):
    def __init__(self, name, arguments):
        self.name = name
        self.values = arguments


class JamSyntaxError(Exception):
    def __init__(self, *arguments):
        self.arguments = arguments

class JamOptionError(Exception):
    def __init__(self, option):
        self.option = option

class JamUserExit(Exception):
    def __init__(self, *message):
        self.message = message

class JamInterrupt(Exception):
    def __init__(self, name, arguments):
        self.name = name
        self.values = arguments

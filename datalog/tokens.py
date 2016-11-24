"""
The tokens used in tokenization and parsing of datalog.
"""

class Token:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

LPAREN = Token('LPAREN')
RPAREN = Token('RPAREN')
COMMA = Token('COMMA')
EQUALS = Token('EQUALS')
NEQUALS = Token('NEQUALS')
WHERE = Token('WHERE')
PERIOD = Token('PERIOD')
TILDE = Token('TILDE')
QUERY = Token('QUESTION')
NAME = Token('NAME')
STRING = Token('STRING')
NUMBER = Token('NUMBER')
LBRACKET = Token('LBRACKET')
RBRACKET = Token('RBRACKET')
AT = Token('AT')

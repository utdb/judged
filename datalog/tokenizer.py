"""
Tokenization module for datalog sources.

The tokenizer is implemented as a hard-coded state machine supported through
several lookup tables.
"""

import datalog
from datalog import TokenizeError
from datalog.tokens import *

# punctuation to token type lookup
punctuation = {
    '(': LPAREN,
    ',': COMMA,
    ')': RPAREN,
    '=': EQUALS,
    '!=': NEQUALS,
    ':-': WHERE,
    '.': PERIOD,
    '~': TILDE,
    '?': QUERY,
    '[': LBRACKET,
    ']': RBRACKET,
    '@': AT
}

# generation of all punctuation starters
punctuation_start = {s[0] for s in punctuation}

# string escape table
string_escapes = {
    'n': '\n',
    '\\': '\\',
    '"': '"',
    '\'': '\'',
    'a': '\a',
    'b': '\b',
    'f': '\f',
    'r': '\r',
    't': '\t',
    'v': '\v'
}

# states
S_NEUTRAL = 0
S_NAME = 1
S_PUNCT = 2
S_COMMENT = 3
S_STRING = 4
S_STRING_ESC = 5
S_NUMBER = 6
S_NUMBER_FRACTIONAL = 7
S_EOF = 8


class LocationContext:
    """
    A location context to allow for informative error messages.

    A location context can be instantiated in several ways: with a single line
    number, or with a start number and an end number. Both start and end values
    given for instantiation may be replaced with other LocationContexts, where
    the start and end values of the 'parent' context are used to determine the
    start and end of the new context.
    """
    def __init__(self, start, stop=None):
        self.start = start
        self.stop = stop or start

        # Correct for construction from other contexts: we only allow widening
        # of intervals.
        if isinstance(self.start, LocationContext):
            self.start = self.start.start
        if isinstance(self.stop, LocationContext):
            self.stop = self.stop.stop

    def __str__(self):
        """
        Produces a human readable line number or range indication.
        """
        result = ':' + str(self.start)
        if self.stop and self.stop != self.start:
            result += '-' + str(self.stop)
        return result

    def __eq__(self, other):
        if other is None or not isinstance(other, LocationContext):
            return False

        return self.start == other.start and self.stop == other.stop

    def __hash__(self):
        return hash((self.start, self.stop))


class Characters:
    """
    Simple character stream on top of an TextIO object.
    """
    def __init__(self, source):
        self.source = source
        self._line = 1
        self._buffer = []

    @property
    def line(self):
        return LocationContext(self._line)

    def next(self):
        """
        Produces the next character or the empty string if the end of file is
        reached.
        """
        if self._buffer:
            c = self._buffer.pop()
        else:
            c = self.source.read(1)
        if c == '\n':
            self._line += 1
        return c

    def push(self, c):
        """
        Pushes back a character.
        """
        if c == '\n':
            self._line -= 1
        self._buffer.append(c)

    def __iter__(self):
        """
        Provides pushback aware iteration over all characters.
        """
        c = self.next()
        while c:
            yield c
            c = self.next()


def isidentifier(c):
    """
    Test to determine if a character can be part of an identifier.
    """
    return c not in punctuation_start and not c.isspace() and not c == '%' and not c == '"'


def number(spelling):
    """
    Number construction helper.

    This helper tries to cast the number as an integer. If that is not possible
    it switches over to float representation as a last resort.
    """
    try:
        return int(spelling)
    except ValueError as e:
        try:
            v = float(spelling)
            if v == int(v):
                return int(v)
            return v
        except ValueError as f:
            raise f from e


def tokenize(source):
    """
    Generator function to perform tokenization on a stream of characters.
    """
    cs = Characters(source)
    state = S_NEUTRAL 
    accum = ''
    line = 0
    csi = iter(cs)
    for c in csi:
        if state == S_NEUTRAL:
            # preempt negative number handling
            if c == '-':
                c2 = cs.next()
                if c2.isdigit():
                    cs.push(c2)
                    state = S_NUMBER
                    accum += c
                    line = cs.line
                    continue
                else:
                    cs.push(c2)

            if c.isdigit():
                state = S_NUMBER
                accum += c
                line = cs.line
            elif isidentifier(c):
                state = S_NAME
                accum += c
                line = cs.line
            elif c in punctuation_start:
                state = S_PUNCT
                accum += c
                line = cs.line
            elif c == '%':
                state = S_COMMENT
                line = cs.line
            elif c == '"':
                state = S_STRING
                line = cs.line
            else: #whitespace and unclaimed garbage
                pass

        elif state == S_COMMENT:
            if c == '\n':
                state = S_NEUTRAL
            else:
                continue

        elif state == S_NAME:
            if isidentifier(c):
                accum += c
            else:
                yield (NAME, accum, line)
                cs.push(c)
                accum = ''
                state = S_NEUTRAL

        elif state == S_PUNCT:
            if accum+c in punctuation:
                yield (punctuation[accum+c], accum + c, line)
                accum = ''
                state = S_NEUTRAL
            elif accum in punctuation:
                yield (punctuation[accum], accum, line)
                cs.push(c)
                accum = ''
                state = S_NEUTRAL
            else:
                raise TokenizeError('Unknown punctuation mark.', cs.line)

        elif state == S_STRING:
            if c == '"':
                yield (STRING, accum, line)
                accum = ''
                state = S_NEUTRAL
            elif c == '\\':
                state = S_STRING_ESC
            elif c == '\n':
                raise TokenizeError('Newline in string literal.', cs.line)
            else:
                accum += c

        elif state == S_STRING_ESC:
            if c in string_escapes:
                accum += string_escapes[c]
                state = S_STRING
            elif c in '01234567':
                oct_accum = c
                for i in range(2):
                    c = next(csi, '')
                    if not c:
                        raise TokenizeError('End of file in octal character escape.', cs.line)
                    if c in '01234567':
                        oct_accum += c
                    else:
                        cs.push(c)
                accum += chr(int(oct_accum, base=8))
                state = S_STRING

        elif state == S_NUMBER:
            if c.isdigit():
                accum += c
            elif c == '.':
                # lookahead for a digit after the period
                c2 = cs.next()
                if c2.isdigit():
                    cs.push(c2)
                    accum += c
                    state = S_NUMBER_FRACTIONAL
                else:
                    yield (NUMBER, number(accum), line)
                    cs.push(c2)
                    cs.push(c)
                    accum = ''
                    state = S_NEUTRAL
            else:
                yield (NUMBER, number(accum), line)
                cs.push(c)
                accum = ''
                state = S_NEUTRAL

        elif state == S_NUMBER_FRACTIONAL:
            if c.isdigit():
                accum += c
            else:
                yield (NUMBER, number(accum), line)
                cs.push(c)
                accum = ''
                state = S_NEUTRAL

    # End of file handling
    if state == S_NEUTRAL:
        pass
    elif state == S_NAME:
        yield (NAME, accum, line)
    elif state == S_PUNCT:
        if accum in punctuation:
            yield (punctuation[accum], accum, line)
        else:
            raise TokenizeError('End of file in punctuation.', cs.line)
    elif state == S_STRING:
        raise TokenizeError('End of file in string literal.', cs.line)
    elif state == S_STRING_ESC:
        raise TokenizeError('End of file in string escape.', cs.line)
    elif state in (S_NUMBER, S_NUMBER_FRACTIONAL):
        try:
            yield (NUMBER, number(accum), line)
        except ValueError as e:
            raise TokenizeError('End of file in number.', cs.line) from e

"""
High level parser that processes a token stream to produce clauses and actions.

The parser structure is a recursive descent parser with look ahead N through an
unlimited pushback buffer.
"""

import datalog
from datalog import tokenizer
from datalog.tokens import *
from datalog import worlds

from datalog import ParseError
from datalog.tokenizer import LocationContext


class Tokens:
    """
    Token stream wrapper to allow intuitive inspection and consumption of
    tokens produced by the tokenization phase.
    """
    def __init__(self, tokens):
        self._tokens = tokens
        self._buffer = []

    def _next(self):
        """Returns the next token."""
        if self._buffer:
            return self._buffer.pop()
        else:
            return next(self._tokens, None)

    def next(self, test=lambda t: True, message='Expected a token.'):
        """
        Returns the next token if it succeeds the test. If it fails an error is
        raised.
        """
        t = self._next()
        if t is None or not test(t):
            raise ParseError(message, t[2] if t is not None else None)
        return t

    def expect(self, token_type, message=''):
        """
        Returns the next token if it matches the given token type. If it does
        not match the token type, and error is raised.
        """
        fmessage = (' ' + message) if message else ''
        return self.next(lambda t: t[0] == token_type,
                    "Expected a token of type {}{}.".format(token_type, fmessage))

    def test(self, test=lambda t: False):
        """Checks if the next token succeeds the test."""
        t = self._next()
        result = t is not None and test(t)
        self.push(t)
        return result

    def test_for(self, token_type):
        """Checks if the next token is of the specified type."""
        return self.test(lambda t: t[0] == token_type)

    def consume(self, token_type):
        """
        Consumes the next token if it matches the token type, if the test fails
        the token remains. The result of the test is returned.
        """ 
        result = self.test_for(token_type)
        if result:
            self.expect(token_type)
        return result

    def push(self, t):
        """Pushes back a token for later consumption."""
        self._buffer.append(t)

    def peek(self):
        """Returns the next token without consuming it."""
        t = self._next()
        if t is not None:
            self.push(t)
        return t

    def is_empty(self):
        """Check if the token stream is empty."""
        t = self._next()
        if t is not None:
            self.push(t)
            return False
        return True

    def __bool__(self):
        return not self.is_empty()


def parse(reader):
    """Helper function to act as single point of entry for simple parses."""
    yield from _parse(tokenizer.tokenize(reader))


# identifier token filter
IDENTIFIER = lambda t: t[0] in (NAME, STRING, NUMBER)

# action mappings
actions = {
    PERIOD: 'assert',
    TILDE: 'retract',
    QUERY: 'query',
    AT: 'annotate'
}


def _parse(tokens):
    """
    Parser entry point. This generator will yield a tuple of (clause, action,
    context) per parsed clause.
    """
    ts = Tokens(tokens)

    while ts:
        start_t = ts.peek()
        if ts.consume(AT):
            annotation = parse_annotation(ts)
            t_action = ts.next(lambda t: t[0] == PERIOD, 'Expected period to close annotation')
            yield(annotation, actions[AT], LocationContext(start_t[2], t_action[2]))
        else:
            clause = parse_clause(ts)
            t_action = ts.next(lambda t: t[0] in (PERIOD, TILDE, QUERY), 'Expected period, tilde or question mark to indicate action.')
            action = actions[t_action[0]]

            if action == 'query':
                if len(clause) > 0:
                    raise ParseError('Can not query for a clause (only literals can be queried on).', t_action[2])
                yield (clause.head, action, LocationContext(start_t[2], t_action[2]))
            else:
                yield (clause, action, LocationContext(start_t[2], t_action[2]))


def make_term(token):
    """
    Helper to convert a token into either a variable or constant term.

    Constant terms are prefixed with a type indicator to ensure intuitive
    handling of strings, names and numbers.
    """
    kind, spelling, location = token

    # See if this is a variable
    if kind == NAME and spelling[:1].isupper():
        return datalog.Variable(spelling)

    # See if this is a do not care variable
    if kind == NAME and spelling == '_':
        return datalog.make_fresh_var()

    # handle constants
    if kind == NAME:
        return datalog.Constant(spelling)
    elif kind == STRING:
        return datalog.Constant(str(spelling), kind='string', data=spelling)
    elif kind == NUMBER:
        return datalog.Constant(str(spelling), kind='number', data=spelling)


def parse_literal(ts):
    """
    Parses a single literal from the token stream.
    """
    pred = None
    terms = []
    polarity = True

    polarity = not ts.consume(TILDE)
    pred = ts.next(IDENTIFIER, 'Expected an identifier or string as predicate or start of equality.')

    if ts.consume(LPAREN):
        # normal literal
        terms.append(ts.next(IDENTIFIER, 'Expected an identifier or string as literal term.'))
        while ts.consume(COMMA):
            terms.append(ts.next(IDENTIFIER, 'Expected an identifier or string as literal term.'))
        ts.expect(RPAREN, 'to close literal with terms')

    elif ts.test_for(EQUALS):
        # infix equals sign
        terms.append(pred)
        pred = ts.expect(EQUALS)
        terms.append(ts.next(IDENTIFIER, 'Expected an identifier or string as right hand side of equality.'))

    elif ts.test_for(NEQUALS):
        # infix not equals sign
        terms.append(pred)
        pred = ts.expect(NEQUALS)
        pred = (EQUALS, '=', pred[2])
        polarity = False
        terms.append(ts.next(IDENTIFIER, 'Expected an identifier or string as right hand side of inequality.'))

    # Sanity check on predicate names
    if pred[0] not in (NAME, EQUALS):
        raise ParseError('Expected a name as predicate.', pred[2])

    # convert the tokens to a literal
    predicate = datalog.Predicate(pred[1], len(terms))
    body = [make_term(t) for t in terms]
    return datalog.Literal(predicate, body, polarity)


def parse_descriptive_label(ts):
    partitioning = ts.next(IDENTIFIER, 'Expected an identifier or string as partitioning of label in descriptive sentence.')

    if partitioning[1] == 'true':
        return worlds.Top()
    elif partitioning[1] == 'false':
        return worlds.Bottom()
    else:
        ts.expect(EQUALS, 'as part of a label')
        part = ts.next(IDENTIFIER, 'Expected an identifier or string as as part of a label in descriptive sentence.')
        return worlds.Label(partitioning[1], part[1])


def parse_sentence_leaf(ts):
    """
    Parses a label, or a parenthesis enclosed sentence.
    """
    if ts.consume(LPAREN):
        result = parse_sentence(ts)
        ts.expect(RPAREN, 'to close expression')
        return result
    else:
        return parse_descriptive_label(ts)


def parse_sentence_not_test(ts):
    """
    Parses a negation or a leaf.
    """
    if ts.test(lambda t: t[1] == 'not'):
        ts.next()
        return worlds.Negation(parse_sentence_not_test(ts))
    else:
        return parse_sentence_leaf(ts)


def parse_sentence_and_test(ts):
    """
    Tries to parse an and operation.
    """
    left = parse_sentence_not_test(ts)
    if ts.test(lambda t: t[1] == 'and'):
        ts.next()
        right = parse_sentence_and_test(ts)
        return worlds.Conjunction(left, right)
    else:
        return left


def parse_sentence_or_test(ts):
    """
    Tries to parse an or operation.
    """
    left = parse_sentence_and_test(ts)
    if ts.test(lambda t: t[1] == 'or'):
        ts.next()
        right = parse_sentence_or_test(ts)
        return worlds.Disjunction(left, right)
    else:
        return left


def parse_sentence(ts):
    """
    Parse a descriptive sentence.
    """
    return parse_sentence_or_test(ts)


def parse_clause(ts):
    """
    Parse a clause.
    """
    head = parse_literal(ts)
    literals = []
    sentence = worlds.Top()

    if ts.consume(WHERE):
        literals.append(parse_literal(ts))
        while ts.consume(COMMA):
            literals.append(parse_literal(ts))

    if ts.consume(LBRACKET):
        sentence = parse_sentence(ts)
        ts.expect(RBRACKET)

    return datalog.Clause(head, literals, [], sentence)


def parse_probability(ts):
    """
    Parse a probability notation of 'P(x=n)'.
    """
    ts.next(lambda t: t[0] == NAME and t[1] in ('P','p'), 'Expected a probability notation of the form P(x=n).')
    ts.expect(LPAREN)
    label = parse_descriptive_label(ts)
    ts.expect(RPAREN)
    return label


def parse_probability_var(ts):
    """
    Parse a probability notation of 'P(x)'.
    """
    ts.next(lambda t: t[0] == NAME and t[1] in ('P','p'), 'Expected a probability notation of the form P(x)')
    ts.expect(LPAREN)
    variable = ts.next(IDENTIFIER, 'Expected an identifier or string as partitioning name.')
    ts.expect(RPAREN)
    return variable

def parse_annotation(ts):
    """
    Parse an annotation.
    """
    if ts.test(lambda t: t[0] == NAME and t[1] in ('P','p')):
        label = parse_probability(ts)
        ts.expect(EQUALS,'to continue probability assignment')
        prob_t = ts.expect(NUMBER, 'to complete probability assignment.')
        return ('probability', label, prob_t[1])
    elif ts.test(lambda t: t[0] == NAME and t[1] == 'uniform'):
        ts.expect(NAME)
        prob_t = parse_probability_var(ts)
        return ('distribution', prob_t[1], 'uniform')
    else:
        t = ts.peek()
        raise ParseError('Expected explicit probability assignment or distribution assignment.', t[2] if t is not None else None)


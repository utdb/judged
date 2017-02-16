"""
High level parser that processes a token stream to produce clauses and actions.

The parser structure is a recursive descent parser with look ahead N through an
unlimited pushback buffer.
"""

import judged
from judged import tokenizer
from judged.tokens import *
from judged import worlds

from judged import ParseError
from judged.tokenizer import LocationContext


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

    def expect_keyword(self, spelling, message=''):
        """
        Returns the next token if it is a a NAME and has the given spelling. If
        it does not match this specification, an error is raised.
        """
        fmessage = (' ' + message) if message else ''
        return self.next(lambda t: t[0] == NAME and t[1] == spelling,
                    "Expected the keyword '{}'{}".format(spelling, fmessage))

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
        return judged.Variable(spelling)

    # See if this is a do not care variable
    if kind == NAME and spelling == '_':
        return judged.make_fresh_var()

    # handle constants
    if kind == NAME:
        return judged.Constant.symbol(spelling)
    elif kind == STRING:
        return judged.Constant.string(spelling)
    elif kind == NUMBER:
        return judged.Constant.number(spelling)


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
    predicate = judged.Predicate(pred[1], len(terms))
    body = [make_term(t) for t in terms]
    return judged.Literal(predicate, body, polarity)


def parse_descriptive_label(ts):
    partitioning = ts.next(IDENTIFIER, 'Expected an identifier or string as partitioning of label in descriptive sentence.')

    if partitioning[1] == 'true':
        return worlds.Top()

    elif partitioning[1] == 'false':
        return worlds.Bottom()

    else:
        left_name = partitioning
        terms = []
        if ts.consume(LPAREN):
            if not ts.consume(RPAREN):
                terms.append(ts.next(IDENTIFIER, 'Expected a variable name or constant in a label function.'))
                while ts.consume(COMMA):
                    terms.append(ts.next(IDENTIFIER, 'Expected a variable name or constant in a label function.'))
                ts.expect(RPAREN, 'to close a label function')
            left = worlds.LabelFunction(left_name[1], tuple(make_term(t) for t in terms))
        else:
            left = worlds.LabelConstant(left_name[1])

        ts.expect(EQUALS, 'as part of a label')

        right_name = ts.next(IDENTIFIER, 'Expected an identifier or string as as part of a label in descriptive sentence.')
        terms = []
        if ts.consume(LPAREN):
            if not ts.consume(RPAREN):
                terms.append(ts.next(IDENTIFIER, 'Expected a variable name or constant in a label function.'))
                while ts.consume(COMMA):
                    terms.append(ts.next(IDENTIFIER, 'Expected a variable name or constant in a label function.'))
                ts.expect(RPAREN, 'to close a label function')
            right = worlds.LabelFunction(right_name[1], tuple(make_term(t) for t in terms))
        else:
            right = worlds.LabelConstant(right_name[1])

        return worlds.Label(left, right)


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

    return judged.Clause(head, literals, [], sentence)


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
    # FIXME: Needs to allow variables
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
        left_name = ts.next(IDENTIFIER, 'Expect an identifier as partitioning name or label function name.')
        terms = []
        if ts.consume(LPAREN):
            if not ts.consume(RPAREN):
                terms.append(ts.next(IDENTIFIER, 'Expected a variable name or constant in a label function.'))
                while ts.consume(COMMA):
                    terms.append(ts.next(IDENTIFIER, 'Expected a variable name or constant in a label function.'))
                ts.expect(RPAREN, 'to close a label function')
            left = worlds.LabelFunction(left_name[1], tuple(make_term(t) for t in terms))
        else:
            left = worlds.LabelConstant(left_name[1])
        return ('distribution', left, 'uniform')

    elif ts.test(lambda t: t[0] == NAME and t[1] == 'use'):
        use_annotation = parse_use_annotation(ts)
        return ('use_module', use_annotation)

    elif ts.test(lambda t: t[0] == NAME and t[1] == 'from'):
        return ('from_module', parse_from_annotation(ts))

    else:
        t = ts.peek()
        raise ParseError('Expected explicit probability assignment, distribution assignment, use statement, or from statement.', t[2] if t is not None else None)


def parse_use_annotation(ts):
    """
    Parse a `use "name"` or `use "name" with key="value", key="value"`.
    """
    ts.consume(NAME)
    module_name = ts.expect(STRING, 'to indicate which module to use')[1]
    module_config = {}

    if ts.test(lambda t: t[0] == NAME and t[1] == 'with'):
        ts.expect(NAME)
        expects_config = True
        while expects_config:
            key = ts.expect(NAME, 'as the configuration key name')[1]
            ts.expect(EQUALS, 'to separate configuration key and value')
            value = ts.expect(STRING, 'as the value for the configuration key')[1]
            module_config[key] = value
            expects_config = ts.consume(COMMA)
    return module_name, module_config


def parse_from_annotation(ts):
    """
    Parse a `from "name" use name` and variants.
    """
    ts.consume(NAME)
    module_name = ts.expect(STRING, 'to indicate from which module to use')[1]
    if ts.test(lambda t: t[0] == NAME and t[1] =='use'):
        ts.expect(NAME, 'the keyword \'use\'')
        predicate_name = ts.expect(NAME, 'as the predicate name to use, or the indicator \'all\' to use all predicates')[1]
        alias_name = None
        if predicate_name == 'all':
            return (module_name, None, None)
        else:
            if ts.test(lambda t: t[0] == NAME and t[1] == 'as'):
                ts.expect(NAME, 'to separate used predicate and alias')
                alias_name = ts.expect(NAME, 'to give the alias under which the predicate should be used')[1]
            return (module_name, predicate_name, alias_name)
    else:
        t = ts.peek()
        raise ParseError('Expected keyword \'use\' to indicate which predicates to use from the module.', t[2] if t is not None else None)

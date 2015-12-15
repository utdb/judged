"""
String formatting for datalog output.
"""

string_escapes = str.maketrans({
    '\n': '\\n',
    '\\': '\\\\',
    '"' : '\\"',
    '\'': '\\\'',
    '\a': '\\a',
    '\b': '\\b',
    '\f': '\\f',
    '\r': '\\r',
    '\t': '\\t',
    '\v': '\\v'
})

default_format_spec = 'plain'

def color(style):
    def apply(s):
        return '\x1b['+style+'m' + s + '\x1b[0m'
    return apply

color.constant = color('01;34')
color.variable = color('01;33')
color.predicate = color('01;32')
color.comment = color('37')
color.sentence = color('01;35')


def html(pre, post):
    def apply(s):
        return pre + s + post
    return apply

html.constant = html('<var class="const">', '</var>')
html.variable = html('<var>', '</var>')
html.predicate = html('<var class="lit">', '</var>')
html.comment = html('<span class="comment">', '</span>')
html.sentence = html('<var class="prob">', '</var>')


def constant(const, format_spec=None):
    """
    Formats a constant for output.
    """
    format_spec = format_spec or default_format_spec
    effect = lambda x: x
    if format_spec == 'color':
        effect = color.constant
    elif format_spec == 'html':
        effect = html.constant

    if const.kind == 'string':
        s = '"' + const.data.translate(string_escapes) + '"'
    else:
        s = const.name if const.data is None else str(const.data)

    return effect(s)


def variable(var, format_spec=None):
    """
    Formats a variable for output.
    """
    format_spec = format_spec or default_format_spec

    effect = lambda x: x
    if format_spec == 'color':
        effect = color.variable
    elif format_spec == 'html':
        effect = html.variable

    return effect(var.name)


def predicate(pred, format_spec=None):
    """
    Formats a predicate for output.
    """
    format_spec = format_spec or default_format_spec

    effect = lambda x: x
    if format_spec == 'color':
        effect = color.predicate
    elif format_spec == 'html':
        effect = html.predicate

    return effect(pred.id)


def literal(lit, format_spec=None):
    """
    Formats a literal for output.
    """
    from datalog import primitives

    format_spec = format_spec or default_format_spec

    pred_effect = lambda x: x
    if format_spec == 'color':
        pred_effect = color.predicate
    elif format_spec == 'html':
        pred_effect = html.predicate

    # special case the equals predicate to infix notation
    if lit.pred == primitives.EQUALS_PREDICATE:
        symbol = ' = ' if lit.polarity else ' != '
        return symbol.join(map(lambda x: format(x, format_spec), lit.terms))

    polarity = '' if lit.polarity else '~'
    result = polarity + pred_effect(lit.pred.name)
    if lit.terms:
        result += '(' + ', '.join(map(lambda x: format(x, format_spec), lit.terms)) + ')'

    return result


def clause(cl, format_spec=None):
    """
    Formats a clause for output.
    """
    from datalog import worlds

    format_spec = format_spec or default_format_spec

    result = format(cl.head, format_spec)
    if cl.body or cl.delayed:
        result += ' :-'
    if cl.body:
        result += ' ' + ', '.join(map(lambda x: format(x, format_spec), cl.body))
    if cl.delayed:
        result += ' | ' + ', '.join(map(lambda x: format(x, format_spec), cl.delayed))

    if cl.sentence and cl.sentence != worlds.Top():
        result += ' [' + format(cl.sentence, format_spec) + ']'
    return result


def comment(com, format_spec=None):
    """
    Formats a comment for output.
    """
    format_spec = format_spec or default_format_spec

    effect = lambda x: x
    if format_spec == 'color':
        effect = color.comment
    elif format_spec == 'html':
        effect = html.comment

    return effect(com)


def sentence(s, format_spec=None):
    """
    Formats a sentence for output.
    """

    format_spec = format_spec or default_format_spec

    effect = lambda x: x
    if format_spec == 'color':
        effect = color.sentence
    elif format_spec == 'html':
        effect = html.sentence

    return effect(str(s))

from tests.lawful import test, run_tests

from judged import tokenizer
from judged import parser

import io
import difflib


@test.parser
def parse():
    source="""% Equality test
ancestor(A, B) :-
    parent(A, B).
ancestor(A, B) :-
    parent(A, C),
    D = C,      % Unification required
    ancestor(D, B).
sibling(A, B) :-
    parent(P, A),
    parent(P, B),
    A != B. % negation required
parent(john, douglas).
parent(john, mary).
parent(bob, john).
parent(ebbon, bob).
ancestor(A, B)?
"""
    expected="""assert{ ancestor(A, B) :- parent(A, B) }
assert{ ancestor(A, B) :- parent(A, C), D = C, ancestor(D, B) }
assert{ sibling(A, B) :- parent(P, A), parent(P, B), A != B }
assert{ parent(john, douglas) }
assert{ parent(john, mary) }
assert{ parent(bob, john) }
assert{ parent(ebbon, bob) }
query{ ancestor(A, B) }"""

    tokens = tokenizer.tokenize(io.StringIO(source))

    buffer = []
    for e in parser._parse(tokens):
        buffer.append("{}{{ {} }}".format(e[1], e[0]))

    result = '\n'.join(buffer)

    if result != expected:
        result_lines = (result+'\n').splitlines(keepends=True)
        expected_lines = (expected+'\n').splitlines(keepends=True)
        d = difflib.Differ()
        result = ['--- result\n','+++ expected\n', '\n']
        result.extend(d.compare(result_lines, expected_lines))
        message = ''.join(result)
        assert result == expected, message


def parse_statement(source):
    tokens = tokenizer.tokenize(io.StringIO(source))
    return next(parser._parse(tokens))

@test.parser
def prob_annotation():
    from judged.worlds import Label

    a = parse_statement('@p(x=1) = 0.5.')
    assert a[1] == 'annotate'
    assert a[0] == ('probability', Label('x',1), 0.5)

@test.parser
def use_annotation():
    a = parse_statement('@use "fooext".')
    assert a[1] == 'annotate'
    assert a[0] == ('use_module', ('fooext', {}))

    b = parse_statement('@use "fooext" with x="XXX", y="YYY".')
    assert b[1] == 'annotate'
    assert b[0] == ('use_module', ('fooext', {'x': 'XXX', 'y': 'YYY'}))


@test.parser
def from_annotation():
    a = parse_statement('@from "fooext" use foo.')
    assert a[1] == 'annotate'
    assert a[0] == ('from_module', ('fooext', 'foo', None))

    b = parse_statement('@from "fooext" use foo as bar.')
    assert b[1] == 'annotate'
    assert b[0] == ('from_module', ('fooext', 'foo', 'bar'))

    c = parse_statement('@from "fooext" use all.')
    assert c[1] == 'annotate'
    assert c[0] == ('from_module', ('fooext', None, None))

from tests.lawful import test, run_tests
from judged.tokenizer import *
from judged.tokens import *


lc = LocationContext

@test.parser
def tokenizer_simple():
    import io

    source = """% Equality test
ancestor(A, B) :-
    parent(A, B).
ancestor(A, B) :-
    parent(A, C),
    D = C,      % Unification required
    ancestor(D, B).
parent("john", douglas).
parent(bob, "john").
parent(1337, bob).
ancestor(A, B)?
"""

    result = [
        (NAME, "ancestor", lc(2)),
        (LPAREN, "(", lc(2)),
        (NAME, "A", lc(2)),
        (COMMA, ",", lc(2)),
        (NAME, "B", lc(2)),
        (RPAREN, ")", lc(2)),
        (WHERE, ":-", lc(2)),
        (NAME, "parent", lc(3)),
        (LPAREN, "(", lc(3)),
        (NAME, "A", lc(3)),
        (COMMA, ",", lc(3)),
        (NAME, "B", lc(3)),
        (RPAREN, ")", lc(3)),
        (PERIOD, ".", lc(3)),
        (NAME, "ancestor", lc(4)),
        (LPAREN, "(", lc(4)),
        (NAME, "A", lc(4)),
        (COMMA, ",", lc(4)),
        (NAME, "B", lc(4)),
        (RPAREN, ")", lc(4)),
        (WHERE, ":-", lc(4)),
        (NAME, "parent", lc(5)),
        (LPAREN, "(", lc(5)),
        (NAME, "A", lc(5)),
        (COMMA, ",", lc(5)),
        (NAME, "C", lc(5)),
        (RPAREN, ")", lc(5)),
        (COMMA, ",", lc(5)),
        (NAME, "D", lc(6)),
        (EQUALS, "=", lc(6)),
        (NAME, "C", lc(6)),
        (COMMA, ",", lc(6)),
        (NAME, "ancestor", lc(7)),
        (LPAREN, "(", lc(7)),
        (NAME, "D", lc(7)),
        (COMMA, ",", lc(7)),
        (NAME, "B", lc(7)),
        (RPAREN, ")", lc(7)),
        (PERIOD, ".", lc(7)),
        (NAME, "parent", lc(8)),
        (LPAREN, "(", lc(8)),
        (STRING, "john", lc(8)),
        (COMMA, ",", lc(8)),
        (NAME, "douglas", lc(8)),
        (RPAREN, ")", lc(8)),
        (PERIOD, ".", lc(8)),
        (NAME, "parent", lc(9)),
        (LPAREN, "(", lc(9)),
        (NAME, "bob", lc(9)),
        (COMMA, ",", lc(9)),
        (STRING, "john", lc(9)),
        (RPAREN, ")", lc(9)),
        (PERIOD, ".", lc(9)),
        (NAME, "parent", lc(10)),
        (LPAREN, "(", lc(10)),
        (NUMBER, 1337, lc(10)),
        (COMMA, ",", lc(10)),
        (NAME, "bob", lc(10)),
        (RPAREN, ")", lc(10)),
        (PERIOD, ".", lc(10)),
        (NAME, "ancestor", lc(11)),
        (LPAREN, "(", lc(11)),
        (NAME, "A", lc(11)),
        (COMMA, ",", lc(11)),
        (NAME, "B", lc(11)),
        (RPAREN, ")", lc(11)),
        (QUERY, "?", lc(11))
    ]

    tokens = list(tokenize(io.StringIO(source)))
    assert tokens == result

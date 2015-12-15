from test.lawful import test, run_tests

from datalog import tokenizer
from datalog import parser


@test.parser
def parse():
    import io

    source = """% Equality test
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

    expected = """assert{ ancestor(A, B) :- parent(A, B) }
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

    assert result == expected


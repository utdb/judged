"""
The definitions of builtin predicates.
"""

from judged import Predicate, Literal, Constant, Clause


# Defines the built-in equality predicate '='
EQUALS_PREDICATE = Predicate('=', 2)

def equals_predicate(literal, prover):
    """
    Equals predicate works by attempting unification.
    """
    a = literal[0]
    b = literal[1]

    env = a.unify(b, {})

    if env is not None:
        a = a.subst(env)
        b = b.subst(env)

    if a == b:
        yield Clause(Literal(literal.pred, [a, b]), [])


def register_primitives(kb):
    kb.add_primitive(EQUALS_PREDICATE, equals_predicate)

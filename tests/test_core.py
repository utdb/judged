#!/usr/bin/env python3.4

from tests.lawful import test, run_tests

import judged
from judged.logic import Knowledge, Prover
from judged.worlds import Top

var = judged.Variable
const = judged.Constant
pred = judged.Predicate
lit = judged.Literal
clause = judged.Clause

@test.core
def interalization():
    a1 = var('A')
    a2 = var('A')
    b1 = var('B')
    assert a1 == a2
    assert a1 != b1
    assert hash(a1) == hash(a2)


@test.core
def literal_id():
    p1 = pred('x', 2)
    p2 = pred('y', 2)

    l1 = lit(p1, [const('alice'), var('A')])
    l2 = lit(p1, [const('alice'), var('A')])
    l3 = lit(p1, [const('alice'), var('B')])
    l4 = lit(p1, [var('A'), var('B')])
    l5 = lit(p2, [var('A'), var('B')])
    l6 = lit(p1, [const('alice'), var('A')], False)

    assert l1.id == l1.id
    assert l1 == l1

    assert l1.id == l2.id
    assert l1 == l2

    assert l1.id != l3.id
    assert l1 != l3

    assert l4.id != l5.id
    assert l4 != l5

    assert l6.id != l1.id
    assert l6 != l1

@test.core
def tags():
    p1 = pred('x', 2)
    p2 = pred('y', 2)

    l1 = lit(p1, [const('alice'), var('A')])
    l2 = lit(p1, [const('alice'), var('B')])
    l3 = lit(p1, [var('A'), var('B')])
    l4 = lit(p2, [var('A'), var('B')])
    l5 = lit(p1, [const('alice'), var('B')], False)

    assert l1.tag() == l2.tag()
    assert l1.tag() != l3.tag()
    assert l3.tag() != l4.tag()
    assert l1.tag() != l5.tag()


@test.core
def subst():
    p1 = pred('x', 2)

    l1 = lit(p1, [const('alice'), const('mary')])
    l2 = lit(p1, [const('alice'), var('A')])

    assert l1.id == l2.subst({var('A'): const('mary')}).id

    l3 = lit(p1, [const('alice'), const('mary')], False)
    l4 = lit(p1, [const('alice'), var('A')], False)

    assert l3.id == l4.subst({var('A'): const('mary')}).id


@test.core
def shuffle():
    def vars(literal):
        return {t for t in literal if not t.is_const()}

    l1 = lit(pred('x', 2), [var('X'), var('Y')])
    l2 = l1.rename()

    assert vars(l1).isdisjoint(vars(l2))


@test.core
def unify():
    p1 = pred('x', 2)
    p2 = pred('y', 2)

    l1 = lit(p1, [const('alice'), var('A')])
    l2 = lit(p1, [const('alice'), var('B')])
    assert l1.unify(l2) == {var('A'): var('B')}

    l3 = lit(p1, [var('A'), var('B')])
    assert l2.unify(l3) == {var('A'): const('alice')}

    l4 = lit(p2, [var('A'), var('B')])
    assert l3.unify(l4) is None

    l5 = lit(p1, [const('alice'), var('A')])
    l6 = lit(p1 ,[const('mary'), var('B')])
    assert l5.unify(l6) is None


@test.core
def contains():
    l1 = lit(pred('x',2), [const('alice'), var('A')])

    assert const('alice') in l1
    assert var('A') in l1
    assert var('B') not in l1


@test.core
def lit_set():
    l1 = lit(pred('x',2), [const('alice'), var('A')])
    l2 = lit(pred('x',2), [const('alice'), var('A')])
    l3 = lit(pred('x',2), [const('alice'), var('A')], False)

    assert {l1,} == {l2,}
    assert {l1,} != {l3,}
    assert l2 in {l1,}
    assert l2 not in {10,20}
    assert 10 not in {l1, l2}
    assert l3 not in {l1, l2}

    s1 = {l1, l2}
    s1.add(l2)
    assert len(s1) == 1

    s2 = {l1, l3}
    s2.add(l2)
    assert len(s2) == 2

@test.core
def literal_grounded():
    p1 = pred('x', 2)
    p2 = pred('y', 2)

    l1 = lit(p1, [const('alice'), var('A')])
    l2 = lit(p1, [const('alice'), const('mary')])
    l3 = lit(p1, [var('A'), var('B')])
    l4 = lit(p1, [const('alice'), var('A')], False)

    assert not l1.is_grounded()
    assert l2.is_grounded()
    assert not l3.is_grounded()
    assert not l4.is_grounded()


@test.core
def clause_id():
    l1 = lit(pred('x',2), [const('alice'), var('A')])
    l2 = lit(pred('y',1), [var('A')])
    l3 = lit(pred('y',1), [var('A')], False)

    c1 = clause(l1, [l2])
    c2 = clause(l1, [l2])

    c3 = clause(l2, [l1])

    assert c1.id == c2.id
    assert c1.id != c3.id

    c4 = clause(l1, [l3])

    assert c1.id != c4.id

    c5 = clause(l1, [l3], delayed=[l2])
    c6 = clause(l1, [l3], delayed=[l2])
    assert c5.id == c6.id
    assert c5.id != c4.id


@test.core
def clause_subst():
    l1 = lit(pred('x',2), [const('alice'), var('A')])
    l2 = lit(pred('y',1), [var('A')])
    c1 = clause(l1, [l2])

    l3 = lit(pred('x',2), [const('alice'), const('mary')])
    l4 = lit(pred('y',1), [const('mary')])
    c2 = clause(l3, [l4])

    env = {var('A'): const('mary')}

    assert c1.subst(env).id == c2.id
    assert c1.subst(None).id == c1.id
    assert c1.subst(dict()).id == c1.id

    l5 = lit(pred('x',2), [const('alice'), var('A')])
    l6 = lit(pred('y',1), [var('A')])
    l7 = lit(pred('z',1), [var('B')])
    c3 = clause(l5, [l6], delayed=[l7])

    l8 = lit(pred('x',2), [const('alice'), const('mary')])
    l9 = lit(pred('y',1), [const('mary')])
    l10 = lit(pred('z',1), [const('christy')])
    c4 = clause(l8, [l9], delayed=[l10])

    env = {var('A'): const('mary'), var('B'): const('christy')}

    assert c3.subst(env).id == c4.id
    assert c3.subst(None).id == c3.id
    assert c3.subst(dict()).id == c3.id



@test.core
def clause_shuffle():
    def vars(literal):
        return {t for t in literal if not t.is_const()}

    def cvars(cl):
        result = vars(cl.head)
        for lit in cl:
            result |= vars(lit)
        for lit in cl.delayed:
            result |= vars(lit)
        return result

    l1 = lit(pred('y', 1), [var('X')])
    l2 = lit(pred('x', 2), [var('X'), var('Y')])
    c1 = clause(l1, [l2])

    c2 = c1.rename()
    assert cvars(c1).isdisjoint(cvars(c2))

    l3 = lit(pred('y', 1), [var('X')])
    l4 = lit(pred('x', 2), [var('X'), var('Y')])
    l5 = lit(pred('z', 1), [var('Z')])
    c3 = clause(l1, [l2], delayed=[l5])

    c4 = c3.rename()
    assert cvars(c3).isdisjoint(cvars(c4))


@test.core
def clause_safe():
    kb = Knowledge(None)
    l1 = lit(pred('y', 1), [var('X')])
    l2 = lit(pred('x', 2), [var('X'), var('Y')])

    c1 = clause(l1, [l2])
    c2 = clause(l2, [l1])

    assert kb.is_safe(c1)
    assert not kb.is_safe(c2)

    l3 = lit(pred('z', 3), [var('A'), const('alice'), const('mary')])
    c3 = clause(l3, [l3])
    assert kb.is_safe(c3)

    l4 = lit(pred('z', 1), [var('Z')], False)

    c4 = clause(l1, [l2, l4])
    assert not kb.is_safe(c4)

    l5 = lit(pred('z', 1), [var('X')], False)

    c5 = clause(l1, [l5])
    assert not kb.is_safe(c5)

    c6 = clause(l1, [l2, l5])
    assert kb.is_safe(c6)


@test.prover
def slg_resolve():
    kb = Knowledge(None)
    prover = Prover(kb)

    l1 = lit(pred('x',1), [var('X')])
    l2 = lit(pred('y',2), [var('X'), var('Y')])
    l3 = lit(pred('z',1), [var('Y')])
    l4 = lit(pred('z',1), [const('alice')])

    # x(X) :- y(X,Y), z(Y).
    c1 = clause(l1, [l2, l3])
    # z(alice).
    c2 = clause(l4)

    # x(X) :- y(X, alice).
    ex = clause(l1, [lit(pred('y',2), [var('X'), const('alice')])])

    ans = prover.slg_resolve(c1, l3, c2)
    assert ex.id == ans.id, "{} == {}".format(ex, ans)

    # non-unifiable
    ans = prover.slg_resolve(c1, l3, clause(lit(pred('foo',2), [var('A'), var('B')]), [lit(pred('a',1), [var('A')]), lit(pred('b',1), [var('B')])]))
    assert ans is None


@test.prover
def slg_factor():
    kb = Knowledge(None)
    prover = Prover(kb)

    x = pred('x', 1)
    y = pred('y', 2)
    z = pred('z', 1)

    # x(X) :- y(X,alice), z(alice).
    c1 = clause(lit(x, [var('X')]), [lit(y, [var('X'), const('alice')]), lit(z, [const('alice')]) ])
    # z(alice) :- | z(mary).
    c2 = clause(lit(z, [const('alice')]), [], [lit(z, [const('alice')])])

    # x(X) :- y(X, alice) | z(alice).
    ex = clause(lit(x, [var('X')]), [lit(y, [var('X'), const('alice')])], [lit(z, [const('alice')])])

    ans = prover.slg_factor(c1, lit(z, [const('alice')]), c2)
    assert ex.id == ans.id, "{} == {}".format(ex, ans)

    # tries to factor a non-delayed clause
    ans = prover.slg_factor(c1, lit(z, [const('alice')]), clause(lit(z, [const('alice')]), []))
    assert ans is None




@test.knowledge
def kb():
    kb = Knowledge(None)

    l1 = lit(pred('y', 1), [var('X')])
    l2 = lit(pred('x', 2), [var('X'), var('Y')])
    l3 = lit(pred('z', 1), [var('Y')])

    c1 = clause(l1, [l2, l3])
    kb.assert_clause(c1)
    assert kb.rules

    kb.retract_clause(c1)
    assert not kb.rules


@test.prover
def ask():
    kb = Knowledge(None)
    prover = Prover(kb)

    l1 = lit(pred('y', 1), [var('X')])
    l2 = lit(pred('x', 2), [var('X'), var('Y')])
    l3 = lit(pred('z', 1), [var('Y')])

    c1 = clause(l1, [l2, l3])
    kb.assert_clause(c1)

    for z in ('alice', 'mary', 'susan'):
        head = lit(pred('z',1), [const(z)])
        body = []
        ca = clause(head, body)
        kb.assert_clause(ca)

    for x,y in [('alice', 'mary'), ('susan', 'mary')]:
        head = lit(pred('x',2), [const(x), const(y)])
        body = []
        ca = clause(head, body)
        kb.assert_clause(ca)

    query = lit(pred('y',1),[var('X')])
    answer = prover.ask(query, lambda s: True)

    assert set(answer) == set([ clause(lit(pred('y',1), [const('alice')]),[],[]), clause(lit(pred('y',1), [const('susan')]),[],[]) ])

    query = lit(pred('x',2), [var('X'), const('alice')])
    answer = prover.ask(query, lambda s: True)
    assert not set(answer)

    query = lit(pred('nothere',1), [var('X')])
    answer = prover.ask(query, lambda s: True)
    assert not set(answer)

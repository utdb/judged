#!/usr/bin/env python3.4

from test.lawful import test, run_tests

import judged
from judged.logic import Knowledge
from judged.logic import Prover

var = judged.Variable
const = judged.Constant
pred = judged.Predicate
lit = judged.Literal
clause = judged.Clause

@test.prover
def primitives():
    kb = Knowledge()
    prover = Prover(kb)

    def testpred(literal, prover):
        if literal[0].is_const():
            yield clause(literal)
        else:
            yield clause(lit(literal.pred, [const('foo')]))
            yield clause(lit(literal.pred, [const('bar')]))
            yield clause(lit(literal.pred, [const('baz')]))

    kb.add_primitive(pred('testpred',1), testpred)

    l1 = lit(pred('y', 1), [var('X')])
    l2 = lit(pred('testpred', 1), [var('X')])

    c1 = clause(l1, [l2])
    kb.assert_clause(c1)

    query = lit(pred('y',1),[var('X')])
    answer = prover.ask(query, lambda s: True)
    assert set(answer) == set([ clause(lit(pred('y',1), [const('foo')]),[],[]), clause(lit(pred('y',1), [const('bar')]),[],[]), clause(lit(pred('y',1), [const('baz')]),[],[]) ])

    query = lit(pred('y',2), [const('twelve'), var('X')])
    answer = prover.ask(query, lambda s: True)
    assert not set(answer)

    kb.assert_clause(clause(lit(pred('testpred', 1), [const('quux')]), []))
    query = lit(pred('y',1),[var('X')])
    answer = prover.ask(query, lambda s: True)
    assert set(answer) == set([ clause(lit(pred('y',1), [const('foo')]),[],[]),  clause(lit(pred('y',1), [const('bar')]),[],[]),  clause(lit(pred('y',1), [const('baz')]),[],[]),  clause(lit(pred('y',1), [const('quux')]),[],[])])

    query = lit(pred('y',2), [const('twelve'), var('X')])
    answer = prover.ask(query, lambda s: True)
    assert not set(answer)

@test.prover
def equals():
    kb = Knowledge()
    prover = Prover(kb)

    l1 = lit(pred('y',1), [var('X')])
    l2 = lit(pred('=',2), [var('X'), var('Y')])
    l3 = lit(pred('z',1), [var('Y')])

    c1 = clause(l1, [l2, l3])
    kb.assert_clause(c1)

    for v in ('foo', 'bar'):
        kb.assert_clause(clause(lit(pred('z',1), [const(v)]), []))

    query = lit(pred('y',1),[var('X')])
    answer = prover.ask(query, lambda s: True)
    assert set(answer) == set([clause(lit(pred('y',1), [const('foo')]),[],[]), clause(lit(pred('y',1), [const('bar')]),[],[])])

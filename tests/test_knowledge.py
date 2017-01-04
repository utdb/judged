#!/usr/bin/env python3.4

from tests.lawful import test, run_tests

import judged
import judged.logic
import judged.worlds

var = judged.Variable
const = judged.Constant
pred = judged.Predicate
lit = judged.Literal
clause = judged.Clause

wor = judged.worlds.Disjunction
wand = judged.worlds.Conjunction
wnot = judged.worlds.Negation
wlabel = judged.worlds.Label
wtop = judged.worlds.Top
wbottom = judged.worlds.Bottom

@test.knowledge
def primitives():
    kb = judged.logic.Knowledge()

    l1 = lit(pred('f', 1), [var('X')])
    l2 = lit(pred('g', 1), [var('X')])

    c1 = clause(l1, [l2], [], wand(wlabel('x','1'), wlabel('y','2')))
    kb.assert_clause(c1)

    c2 = clause(l2, [l1], [], wand(wlabel('x','2'), wlabel('y','1')))
    kb.assert_clause(c2)

    assert set(kb.clauses(l1, None)) == {c1}

    answer = set(kb.parts('x'))
    assert answer == {'1', '2'}, str(answer)

    answer = set(kb.parts('y'))
    assert answer == {'1', '2'}, str(answer)

    answer = set(kb.parts('z'))
    assert answer == set(), str(answer)

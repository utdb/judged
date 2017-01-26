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
wlc = judged.worlds.LabelConstant
wlf = judged.worlds.LabelFunction
wl = lambda partition, part: wlabel(wlc(partition), wlc(part))
wtop = judged.worlds.Top
wbottom = judged.worlds.Bottom

@test.knowledge
def primitives():
    kb = judged.logic.Knowledge(None)

    l1 = lit(pred('f', 1), [var('X')])
    l2 = lit(pred('g', 1), [var('X')])

    c1 = clause(l1, [l2], [], wand(wl('x','1'), wl('y','2')))
    kb.assert_clause(c1)

    c2 = clause(l2, [l1], [], wand(wl('x','2'), wl('y','1')))
    kb.assert_clause(c2)

    assert set(kb.clauses(l1)) == {c1}

    answer = set(kb.parts(wlc('x')))
    assert answer == {wlc('1'), wlc('2')}, str(answer)

    answer = set(kb.parts(wlc('y')))
    assert answer == {wlc('1'), wlc('2')}, str(answer)

    answer = set(kb.parts(wlc('z')))
    assert answer == set(), str(answer)


@test.knowledge
def safety():
    kb = judged.logic.Knowledge(None)

    def assert_clause(clause):
        try:
            kb.assert_clause(clause)
        except judged.SafetyError as e:
            return False
        else:
            return True

    l1 = lit(pred('f', 1), [var('X')])
    l2 = lit(pred('g', 1), [var('Y')])

    c1 = clause(l1, [l2], [], wand(wl('x','1'), wl('y','2')))

    assert not assert_clause(c1), "Unsafe clause {} was asserted".format(c1)

    l3 = lit(pred('f', 1), [var('X')])
    l4 = lit(pred('g', 1), [var('X')])

    c2 = clause(l3, [l4], [], wand(wl('x','1'), wlabel(wlf('p', (var('X'),)),wlc('2'))))
    assert assert_clause(c2), "Safe clause {} was rejected".format(c2)

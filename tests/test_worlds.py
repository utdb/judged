#!/usr/bin/env python3.4

import io

from tests.lawful import test

import judged
from judged import tokenizer
from judged import parser
from judged import worlds


class TestKB():
    """ class stores a temporary Knowledge Base just for testing """
    def __init__(self, labels):
        self.labels = labels

    def parts(self, p):
        return {t[1] for t in self.labels if t[0]==p}

def test_equivalent_fun(l, r, extra_labels=set()):
    """ function used for testing Sentence equivalence function """
    return worlds.equivalent(l, r, TestKB(l.labels() | r.labels() | extra_labels) )

def test_falsehood_fun(s, extra_labels=set()):
    return worlds.falsehood(s, TestKB(s.labels() | extra_labels))

def sentence(string):
    reader = io.StringIO(string)
    ts = parser.Tokens(tokenizer.tokenize(reader))
    return parser.parse_sentence(ts)

def label(string):
    reader = io.StringIO(string)
    ts = parser.Tokens(tokenizer.tokenize(reader))
    return parser.parse_descriptive_label(ts).labels().pop()

@test.worlds
def equivalence():
    s1 = sentence('x=1')
    s2 = sentence('y=1')

    assert not test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1)')
    s2 = sentence('(x=2)')
    assert not test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1)')
    s2 = sentence('(not x=2)')
    assert      test_equivalent_fun(s1, s2, {label('x=2')})

    s1 = sentence('(x=1)')
    s2 = sentence('(not x=2)')
    assert not test_equivalent_fun(s1, s2, {label('x=3')})

    s1 = sentence('(x=1)')
    s2 = sentence('(x=1)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('(not x=1)')
    s2 = sentence('(x=1)')
    assert not test_equivalent_fun(s1, s2)

    s1 = sentence('(not x=1)')
    s2 = sentence('(not x=1)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1 and x=2)')
    s2 = sentence('(x=1)')
    assert not test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1 and x=2)')
    s2 = sentence('(x=1 and x=2)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1 and x=2)')
    s2 = sentence('(y=1 and y=2)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1 and x=1)')
    s2 = sentence('(x=1)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('(not x=1 and not x=2)')
    s2 = sentence('not (x=1 or  x=2)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('(x=1 and not x=1)')
    s2 = sentence('(x=2 and not x=2)')
    assert     test_equivalent_fun(s1, s2)

    s1 = sentence('true')
    s2 = sentence('false')
    assert not test_equivalent_fun(s1, s2)

@test.worlds
def falsehoods():
    s1 = sentence('(x=1) and (not x=1)')
    assert      test_falsehood_fun(s1)

    s1 = sentence('(x=1) and (x=2)')
    assert      test_falsehood_fun(s1, {label('x=3')})

    s1 = sentence('(x=1) and (y=2)')
    assert not test_falsehood_fun(s1)


@test.worlds
def optimizing_operations():
    s1 = sentence('x=1')
    s2 = sentence('x=2')
    assert test_equivalent_fun(worlds.conjunct(s1,s2), sentence('x=1 and x=2'))

    s1 = sentence('x=1')
    s2 = sentence('x=2')
    assert test_equivalent_fun(worlds.disjunct(s1,s2), sentence('x=1 or x=2'))

    strue = sentence('true')
    sfalse = sentence('false')
    assert test_equivalent_fun(worlds.conjunct(strue,sfalse), sfalse)
    assert test_equivalent_fun(worlds.disjunct(strue,sfalse), strue)

    assert test_equivalent_fun(worlds.conjunct(strue, strue), strue)
    assert test_equivalent_fun(worlds.disjunct(strue, strue), strue)

    assert test_equivalent_fun(worlds.conjunct(sfalse, sfalse), sfalse)
    assert test_equivalent_fun(worlds.disjunct(sfalse, sfalse), sfalse)


@test.worlds
def substitution():
    var = judged.Variable
    const = judged.Constant

    s1 = sentence('g(C)=1')
    s2 = sentence('g(42)=1')
    env = {var('C'): const.number(42)}
    assert test_equivalent_fun(s1.subst(env), s2)

    s1 = sentence('x=b(test) and a(X,Y)=b(Z)')
    s2 = sentence('x=b(Z) and a("foo", 10)=b(test)')

    assert not s1.is_grounded()
    assert not s2.is_grounded()

    env = {var('X'): const.string("foo"), var('Y'):const.number(10), var('Z'):const.symbol('test')}
    s3 = s1.subst(env)
    s4 = s2.subst(env)

    assert s3.is_grounded()
    assert s4.is_grounded()
    assert test_equivalent_fun(s3, s4)

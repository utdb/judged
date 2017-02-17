from tests.lawful import test, run_tests

from judged import tokenizer
from judged import parser
from judged import actions

import io
import difflib


def parse_statement(source):
    return parser.string_parse(source, parser.parse_action)


@test.parser
def assertion():
    from judged import Clause, Literal, Variable, Constant, Predicate
    a = parse_statement('foo(x).')

    assert type(a) == actions.AssertAction
    assert a.clause == Clause(Literal(Predicate('foo', 1), terms=[Constant.symbol('x')]))


@test.parser
def prob_annotation():
    from judged.worlds import Label, LabelConstant

    a = parse_statement('@p(x=1) = 0.5.')
    assert type(a) == actions.AnnotateProbabilityAction
    assert a.label == Label(LabelConstant('x'), LabelConstant(1))
    assert a.probability == 0.5


@test.parser
def use_annotation():
    a = parse_statement('@use "fooext".')
    assert type(a) == actions.UseModuleAction
    assert a.module == 'fooext'
    assert a.config == {}

    b = parse_statement('@use "fooext" with x="XXX", y="YYY".')
    assert type(b) == actions.UseModuleAction
    assert b.module == 'fooext'
    assert b.config == {'x': 'XXX', 'y': 'YYY'}


@test.parser
def from_annotation():
    a = parse_statement('@from "fooext" use foo.')
    assert type(a) == actions.UsePredicateAction
    assert a.module == 'fooext'
    assert a.predicate == 'foo'
    assert a.alias == None

    b = parse_statement('@from "fooext" use foo as bar.')
    assert type(b) == actions.UsePredicateAction
    assert b.module == 'fooext'
    assert b.predicate == 'foo'
    assert b.alias == 'bar'

    c = parse_statement('@from "fooext" use all.')
    assert type(c) == actions.UsePredicateAction
    assert c.module == 'fooext'
    assert c.predicate == None
    assert c.alias == None

#!/usr/bin/env python3.4

from test.lawful import test, run_tests

import datalog
from datalog import tokenizer
from datalog import parser
from datalog import logic

import io
from pathlib import Path
import difflib


def make_suite(path, root, context_type):
    @test.complex
    def suite():
        expect_file = root / (path.stem + '.txt')
        context = context_type()

        output_buffer = io.StringIO()

        with path.open() as f:
            for clause, action, location in parser.parse(f):
                try:
                    if action == 'assert':
                        context.knowledge.assert_clause(clause)
                    elif action == 'retract':
                        context.knowledge.retract_clause(clause)
                    elif action == 'query':
                        literal = clause.head
                        for a in context.ask(literal).answers:
                            print("{}.".format(a.clause), file=output_buffer)
                except datalog.DatalogError as e:
                    raise AssertionError from e

        expected = []
        output = []

        with expect_file.open() as f: expected = sorted(list(f))
        output = sorted(output_buffer.getvalue().splitlines(keepends=True))

        if output != expected:
            d = difflib.Differ()
            result = ['--- output\n','+++ expected\n', '\n']
            result.extend(d.compare(output, expected))
            message = ''.join(result)
            assert output == expected, message
    suite.__name__ = path.stem


for case in Path('test/cases/deterministic').glob('*.dl'):
    make_suite(case, Path('test/cases/deterministic'), logic.DeterministicContext)

for case in Path('test/cases/exact').glob('*.dl'):
    make_suite(case, Path('test/cases/exact'), logic.ExactContext)

for case in Path('test/cases/montecarlo').glob('*.dl'):
    make_suite(case, Path('test/cases/montecarlo'), logic.MontecarloContext)

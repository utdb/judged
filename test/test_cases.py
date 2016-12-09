#!/usr/bin/env python3.4

from test.lawful import test, run_tests

import datalog
from datalog import tokenizer
from datalog import parser
from datalog import logic

import io
from pathlib import Path
import difflib


def make_suite(path):
    @test.complex
    def suite():
        expect_file = Path('test/cases') / (path.stem + '.txt')
        kb = logic.Knowledge()
        prover = logic.Prover(kb)

        output_buffer = io.StringIO()

        with path.open() as f:
            for clause, action, location in parser.parse(f):
                try:
                    if action == 'assert':
                        kb.assert_clause(clause)
                    elif action == 'retract':
                        kb.retract_clause(clause)
                    elif action == 'query':
                        for a in prover.ask(clause.head, lambda s: True):
                            print("{}.".format(a), file=output_buffer)
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


for case in Path('test/cases').glob('*.dl'):
    make_suite(case)

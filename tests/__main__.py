#!/usr/bin/env python3.4

from tests.lawful import run_tests

from tests import test_core
from tests import test_tokenizer
from tests import test_parser
from tests import test_prover
from tests import test_cases

from tests import test_worlds
from tests import test_knowledge

if __name__ == '__main__':
    run_tests()

"""
Lawful, the simple test framework.
"""

import traceback
import textwrap
import sys
import argparse


def report(message=''):
    """Reports a message."""
    print(message)

def report_exc(message, exc):
    """Reports an unexpected Error."""
    report(message)
    report(textwrap.indent(exc, '    > '))

def checker(f):
    """Produces a callable that checks the given function f."""
    def check():
        name = f.__name__
        message = ''
        if f.__doc__:
            message = '\n' + textwrap.indent(f.__doc__, '    """ ')
        try:
            f()
            return True
        except AssertionError as e:
            if e.args:
                message = e.args[0].strip()
            exception_class, exception, trace = sys.exc_info()
            frames = traceback.extract_tb(trace)
            last = frames[len(frames)-1]

            message_hr = textwrap.indent(message, '    ')

            assertion = "{3}".format(*last)
            position = "{0}:{1}".format(*last)

            report("{} ({}):".format(name, position))
            if message_hr:
                report('    --------------------------------')
                report("{}".format(message_hr))
                report('    --------------------------------')
            report("    {}".format(assertion))
            report('')
            return False
        except Exception as e:
            report_exc("{}:{}".format(name, message), traceback.format_exc())
            return False
    check._test_function = f
    return check


checks = []


class Test:
    """Test decorator to collect tests."""
    def __init__(self, category='default'):
        self.category = category

    def __call__(self, f):
        suite = checker(f)
        checks.append((self.category, suite))
        return f

    def __getattr__(self, name):
        return Test(name)


test = Test()


def run_tests():
    """
    Runs the tests and outputs the failures and score tally.
    """
    parser = argparse.ArgumentParser(description='Tests for the project.')
    parser.add_argument('-l', '--list', default=False, action='store_true',
                        help='Lists all categories and tests.')
    parser.add_argument('-c', '--category', default=[], nargs='*',
                        help='The categories to run.')
    parser.add_argument('-t', '--test', default=[], nargs='*',
                        help='The tests to run.')
    options = parser.parse_args()

    # handle list option
    if options.list:
        categories = {c for c,t in checks}
        for cat in sorted(categories):
            report(cat)
            for t in (t for c,t in checks if c==cat):
                report('    '+t._test_function.__name__)
        return

    # actual test run
    categories = options.category
    selected = options.test
    report('=' * 80)
    report()

    selection = []
    if selected:
        selection.append(', '.join(selected))
    if categories:
        selection.append("all {}".format(categories))
    selection_hr = ' and '.join(selection) if selection else 'all'

    report("Running {} tests for {}".format(selection_hr, sys.argv[0]))
    report()
    success = 0
    failure = 0
    tests = []

    if not categories and not selected:
        tests = checks
    else:
        for c, t in checks:
            if c in categories or t._test_function.__name__ in selected:
                tests.append((c,t))

    for category, check in tests:
        if check():
            success += 1
        else:
            failure += 1

    print("{} / {}".format(success, success + failure))
    report()
    if not failure:
        report('+++ SUCCESS')
    else:
        report('--- FAILURE')
    report()
    report('='*80)
    sys.exit(1 if failure > 0 else 0)

#!/usr/bin/env python3.4
"""
Entry point to provide REPL and file processing.
"""

import datalog
from datalog import tokenizer
from datalog import parser
from datalog import logic
from datalog import formatting
from datalog import caching

import sys
import os
import argparse
import importlib
import traceback


# Public constants
NAME  = 'Datalog'
FLUFF = '^_^'
__version__ = '0.1a1'


# Internal constants
FORMAT_ENV_KEY = 'DATALOG_FORMAT'

# the global knowledge base
kb = logic.Knowledge()


def query(clause, args):
    """Executes a query and presents the answers."""
    if args.verbose:
        print(formatting.comment("% query ") + "{}".format(clause))

    # determine debugger
    debugger = None
    if args.debug:
        debugger = ReportingDebugger()

    # determine cache mechanism
    cache = {'none': caching.NoCache,
             'dict': caching.DictCache}[args.cache]()

    # set up prover and execute query
    prover = logic.Prover(kb, debugger=debugger, cache=cache)
    for a in prover.ask(clause):
        print("{}.".format(a))


def assert_clause(clause, args):
    if args.verbose:
        print(formatting.comment("% assert ") + "{}".format(clause))
    kb.assert_clause(clause)


def retract_clause(clause, args):
    if args.verbose:
        print(formatting.comment("% retract ") + "{}".format(clause))
    kb.retract_clause(clause)


actions = {
    'assert': assert_clause,
    'retract': retract_clause,
    'query': query
}


def handle_reader(reader, args):
    """
    Processes all statements in a single reader. Errors in the handling of an
    action will be furnished with context information based on the context
    information of the parsed action.
    """
    for clause, action, location in parser.parse(reader):
        try:
            actions[action](clause, args)
        except datalog.DatalogError as e:
            e.context = location
            raise e


def batch(readers, args):
    """
    Batch process all readers in turn, taking all actions one after the other.

    Errors will break out of processing immediately.
    """
    for reader in readers:
        try:
            handle_reader(reader, args)
        except datalog.DatalogError as e:
            print("{}{}: {}".format(reader.name, e.context, e.message))
            break


def interactive(args):
    """
    Provides a REPL for asserting and retracting clauses and querying the
    knowledge base.
    """
    import io

    try:
        import readline
    except ImportError:
        pass

    try:
        print("{} {} ({})".format(NAME, __version__, FLUFF))
        print()
        while True:
            line = input('> ')
            try:
                handle_reader(io.StringIO(line), args)
            except datalog.DatalogError as e:
                print("Error: {}".format(e.message))
    except EOFError:
        print()
        return


class ReportingDebugger:
    def __init__(self):
        self.depth = 0

    def indent(self):
        return '  ' * self.depth

    def ask(self, literal):
        print("-" * 80)
        print("Query '{}'".format(literal))

    def done(self, subgoal):
        print("Query completed: {} answers".format(len(subgoal.anss)))
        print("-" * 80)

    def answer(self, literal, clause, selected):
        print("{}Answer for '{}': '{}'".format(self.indent(), literal, clause))

    def clause(self, literal, clause, selected, polarity):
        print("{}Clause for '{}': '{}' (with '{}' selected)".format(self.indent(), literal, clause, selected))

    def subgoal(self, literal):
        print("{}New goal: '{}'".format(self.indent(), literal))
        self.depth += 1

    def complete(self, subgoal):
        self.depth -= 1
        print("{}Completed '{}'".format(self.indent(), subgoal.literal))


def key_value_pair(string):
    parts = string.split('=')
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("'{}' is not a key value pair".format(string))
    config = parts[0].split(':')
    if len(config) != 2:
        raise argparse.ArgumentTypeError("'{}' is not a module:option identifier".format(parts[0]))
    return (config[0], config[1], parts[1])


def main():
    options = argparse.ArgumentParser(description="{} entry point for interactive and batch use of datalog.".format(NAME))
    options.add_argument('file', metavar='FILE', type=argparse.FileType('r', encoding='utf-8'), nargs='*',
                         help='Input files to process in batch.')
    options.add_argument('-i', '--import', default=False, action='store_true', dest='imports',
                         help='Imports the datalog files before going to interactive mode.')
    options.add_argument('-v', '--verbose', default=False, action='store_true',
                         help='Increases verbosity. Outputs each imported statement before doing it.')
    options.add_argument('-d', '--debug', default=False, action='store_true',
                         help='Enables debugging output.')
    options.add_argument('-c', '--cache', choices=('dict', 'none'), default='dict',
                         help='Selects the caching method to use. Defaults to the \'dict\' mechanism.')
    options.add_argument('-m', '--module', nargs='*', default=[],
                         help='Any additional modules to load and initialize.')
    options.add_argument('-o', '--option', nargs='*', type=key_value_pair, default={},
                         help='Module options to pass to loaded modules. Options should be formatted in a \'module:option=value\' pattern.')
    format_default = os.environ.get(FORMAT_ENV_KEY, 'color')
    if not sys.stdout.isatty():
        format_default = 'plain'
    options.add_argument('-f', '--format', choices=('plain','color','html'), default=format_default,
                         help='Selects output format. Defaults to the value of the '+FORMAT_ENV_KEY+' environment variable if set, \'plain\' if it is not set or if the output is piped.')

    args = options.parse_args()

    datalog.formatting.default_format_spec = args.format

    for module in args.module:
        config = {k: v for m,k,v in args.option if m==module}
        try:
            mod = importlib.import_module(module)
            mod.initialize(config, kb, actions)
        except ImportError as e:
            if args.verbose:
                options.error(traceback.format_exc())
            else:
                options.error(str(e))

    if args.file:
        batch(args.file, args)
        if args.imports:
            interactive(args)
    else:
        interactive(args)


if __name__ == '__main__':
    main()

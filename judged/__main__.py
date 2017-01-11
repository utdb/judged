#!/usr/bin/env python3.4
"""
Entry point to provide REPL and file processing.
"""

import judged
from judged import context
from judged import tokenizer
from judged import parser
from judged import logic
from judged import formatting
from judged import worlds

import sys
import os
import argparse
import importlib
import traceback


# Public constants
NAME  = 'JudgeD'
FLUFF = '^_^'
__version__ = '0.2'


# Internal constants
FORMAT_ENV_KEY = 'DATALOG_FORMAT'

current_context = None

# FIXME: Refactor the query, assert, retract, and annotate actions to the context
def query(clause, args):
    """Executes a query and presents the answers."""
    if len(clause) > 0:
        raise judged.JudgedError('Cannot query for a clause (only literals can be queried on).')
    if clause.sentence != worlds.Top():
        raise judged.JudgedError('Cannot perform a query with a descriptive sentence.')

    literal = clause.head
    if args.verbose:
        print(formatting.comment("% query ") + "{}".format(literal))

    result = current_context.ask(literal)

    # LATER: `sorted` can be removed for python3.6 with stable dictionaries
    for k in sorted(result.notes):
        print(formatting.comment("% {}: {}".format(k, result.notes[k])))

    for a in result.answers:
        print("{}.".format(a.clause), end='')
        if a.probability is not None:
            print(formatting.comment(" % p = {}".format(a.probability)), end='')
        print()

    # if args.json:
    #     result = dict()
    #     result['iterations'] = count
    #     result['root-mean-square-error'] = error()
    #     result['answers'] = list()
    #     for a, c in sorted(answers.items(), key=lambda t: p(t[1])):
    #         result['answers'].append({
    #             'predicate': str(a.pred.name),
    #             'terms': [str(t) for t in a.terms],
    #             'probability': p(c)
    #         })
    #     json.dump(result, sys.stdout)
    #     print()
    # else:
    #     print(formatting.comment("% iterations: {}".format(count)))
    #     print(formatting.comment("% root-mean-square error: {}".format(error())))
    #     for a, c in sorted(answers.items(), key=lambda t: p(t[1])):
    #         print("{}.".format(a) + formatting.comment("  % p = {}".format(p(c))))


def annotate(annotation, args):
    """
    Handles annotations in the judged source.
    """
    if annotation[0] == 'probability':
        if args.verbose: print(formatting.comment("% annotate ") + "p({}) = {}".format(annotation[1], annotation[2]))
        current_context.add_probability(annotation[1].partitioning, annotation[1].part, annotation[2])
    elif annotation[0] == 'distribution':
        if args.verbose:
            print(formatting.comment("% annotate {} distribution for p({})".format(annotation[2], annotation[1])))

        # determine all present parts
        parts = current_context.knowledge.parts(annotation[1])

        if parts:
            for part in parts:
                current_context.add_probability(annotation[1], part, 1/len(parts))
                print(formatting.comment("%% Setting p({}={}) = {}".format(annotation[1], part, 1/len(parts))))
    else:
        raise judged.JudgedError("Unknown annotation {}".format(annotation))


def assert_clause(clause, args):
    if args.verbose:
        print(formatting.comment("% assert ") + "{}".format(clause))
    current_context.knowledge.assert_clause(clause)


def retract_clause(clause, args):
    if args.verbose:
        print(formatting.comment("% retract ") + "{}".format(clause))
    current_context.knowledge.retract_clause(clause)


actions = {
    'assert': assert_clause,
    'retract': retract_clause,
    'annotate': annotate,
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
        except judged.JudgedError as e:
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
        except judged.JudgedError as e:
            print("{}{}: {}".format(reader.name, e.context, e.message))
            break


def interactive_command(line, args):
    command = line.strip()[1:]
    if command == "kb":
        print(formatting.comment('% Outputting internal KB:'))
        for pred in current_context.knowledge.db:
            print(formatting.comment('%') + " {} =>".format(pred))
            for id, clause in current_context.knowledge.db[pred].items():
                print(formatting.comment('%')+"   {}".format(clause))
    elif command == 'help':
        print(formatting.comment('% available commands: help, kb'))
    else:
        raise judged.JudgedError("Unknown command '{}'".format(command))


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
        print("{} {} ({})".format(NAME + ", {} variant".format(args.type), __version__, FLUFF))
        print()
        while True:
            line = input('> ')
            try:
                if line.strip().startswith('.'):
                    interactive_command(line, args)
                else:
                    handle_reader(io.StringIO(line), args)
            except judged.JudgedError as e:
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

    def note(self, message):
        print(formatting.comment("{}(note:".format(self.indent())), message,formatting.comment(')'))


def main():
    global current_context

    # set up shared options for all prover commands
    shared_options = argparse.ArgumentParser(add_help=False)
    shared_options.add_argument('file', metavar='FILE', type=argparse.FileType('r', encoding='utf-8'), nargs='*',
                         help='Input files to process in batch.')
    shared_options.add_argument('-i', '--import', default=False, action='store_true', dest='imports',
                         help='Imports the judged files before going to interactive mode.')
    shared_options.add_argument('-v', '--verbose', default=False, action='store_true',
                         help='Increases verbosity. Outputs each imported statement before doing it.')
    shared_options.add_argument('-d', '--debug', default=False, action='store_true',
                         help='Enables debugging output.')

    format_default = os.environ.get(FORMAT_ENV_KEY, 'color')
    if not sys.stdout.isatty():
        format_default = 'plain'
    shared_options.add_argument('-f', '--format', choices=('plain','color','html'), default=format_default,
                         help='Selects output format. Defaults to the value of the '+FORMAT_ENV_KEY+' environment variable if set, \'plain\' if it is not set or if the output is piped.')
    # FIXME: Usability feature for later (used in MC branch)
    # shared_options.add_argument('-j', '--json', default=False, action='store_true',
    #                      help='Output query answers in JSON format.')

    # build actual options
    options = argparse.ArgumentParser(description="{} entry point for interactive and batch use of judged.".format(NAME))
    options.set_defaults(type=None)

    suboptions = options.add_subparsers(title='Subcommands for the judged judged system')

    deterministic_options = suboptions.add_parser('deterministic', aliases=['det'], parents=[shared_options],
                         help='Use the deterministic judged prover')
    deterministic_options.set_defaults(type='deterministic')

    # FIXME: Get world selection working
    # deterministic_options.add_argument('-s', '--select', nargs='*',
    #                      help='Restricts to a specific possible world by selecting partitions from the knowledge base.')

    exact_options = suboptions.add_parser('exact', aliases=['ex'], parents=[shared_options],
                         help='Use the exact descriptive sentence judged prover')
    exact_options.set_defaults(type='exact')

    montecarlo_options = suboptions.add_parser('montecarlo', aliases=['mc'], parents=[shared_options],
                         help='Use the Monte Carlo estimated probabilities prover')
    montecarlo_options.set_defaults(type='montecarlo')
    montecarlo_options.add_argument('-n', '--number', type=int, default=1000,
                         help='The maximum number of simulation runs to do. A value of zero means no maximum. Defaults to %(default)s.')
    montecarlo_options.add_argument('-a', '--approximate', type=float, default=0,
                         help='The maximum allowable error for an approximation simulation. Defaults to %(default)s.')

    args = options.parse_args()

    if not args.type:
        options.print_help()
        options.exit()

    # determine debugger
    debugger = None
    if args.debug:
        debugger = ReportingDebugger()

    context_options = {
        'debugger': debugger
    }

    if args.type == 'deterministic':
        current_context = context.DeterministicContext(**context_options)
    elif args.type == 'exact':
        current_context = context.ExactContext(**context_options)
    elif args.type == 'montecarlo':
        current_context = context.MontecarloContext(number=args.number, approximate=args.approximate, **context_options)

    judged.formatting.default_format_spec = args.format

    if args.file:
        batch(args.file, args)
        if args.imports:
            interactive(args)
    else:
        interactive(args)


if __name__ == '__main__':
    main()

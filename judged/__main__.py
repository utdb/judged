#!/usr/bin/env python3.4
"""
Entry point to provide REPL and file processing.
"""

import judged
from judged import context
from judged import actions
from judged import tokenizer
from judged import parser
from judged import logic
from judged import formatting
from judged import worlds
from judged import extensions

import sys
import os
import argparse
import importlib
import traceback
import textwrap
import collections


# Public constants
NAME  = 'JudgeD'
VERSION = '1.0'


# Internal constants
FORMAT_ENV_KEY = 'DATALOG_FORMAT'

current_context = None
args = None


class ActionReporter:
    """
    A reporter to support verbosity and logging of all performed actions.
    Use of this mechanism is optional, and actions perform equally well without
    any form of reporting.

    For the command line interface, this mechanism is used to inform the user of
    the progress of their scripts.
    """
    def __init__(self, args):
        self.verbose = args.verbose
        self.verbose_questions = args.verbose_questions
        self.indent = 0

    def perform(self, action):
        if self.verbose or (type(action) == actions.QueryAction and self.verbose_questions):
            print('  ' * self.indent + formatting.comment("% ") + "{}".format(action))

    def result(self, result):
        # LATER: `sorted` can be removed for python3.6 with stable dictionaries
        for k in sorted(result.notes):
            print('  ' * self.indent + formatting.comment("% {}: {}".format(k, result.notes[k])))

        for a in result.answers:
            print('  ' * self.indent + "{}.".format(a.clause), end='')
            if a.probability is not None:
                print('  ' * self.indent + formatting.comment(" % p = {}".format(a.probability)), end='')
            print()

    def enter(self, action):
        self.indent += 1

    def exit(self):
        self.indent -= 1


def handle_reader(reader):
    """
    Processes all statements in a single reader. Errors in the handling of an
    action will be furnished with context information based on the context
    information of the parsed action.
    """
    # parse the compound action from the reader
    compound = parser.parse(reader)
    # set up the CLI reporter
    reporter =  ActionReporter(args)

    # manually iterate through the compound. This could be done directly with a
    # `compound.perform` invocation, but this allows all the queries in the
    # compound to have their result reported, instead of only the final one.
    for action in compound:
        try:
            action.perform(current_context, reporter)
        except judged.JudgedError as e:
            e.context = action.source
            raise e


def batch(readers):
    """
    Batch process all readers in turn, taking all actions one after the other.

    Errors will break out of processing immediately.
    """
    for reader in readers:
        try:
            handle_reader(reader)
        except judged.JudgedError as e:
            print("{}{}: {}".format(reader.name, e.context, e.message))
            break


def interactive():
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
        print("{name}, {variant} ({version})".format(name=NAME, version=VERSION, variant=current_context.tagline))
        print('Type ".help" for interactive commands.')
        print()
        while True:
            line = input('> ')
            try:
                if line.strip().startswith('.'):
                    interactive_command(line)
                else:
                    handle_reader(io.StringIO(line))
            except judged.JudgedError as e:
                print("Error: {}".format(e.message))
    except EOFError:
        print()
        return


interactive_commands = {}

InteractiveCommand = collections.namedtuple('InteractiveCommand', ['command', 'function', 'description'])

def ic(command, description=''):
    def registerer(f):
        interactive_commands[command] = InteractiveCommand(command, f, description)
        return f
    return registerer

def interactive_command(line):
    if line == '.':
        ic_help([])
        return
    command, *arguments = line[1:].split()
    cmd = interactive_commands.get(command)
    if cmd:
        cmd.function(arguments)
    else:
        raise judged.JudgedError("Unknown interactive command '{}', type .help to get available commands".format(command))


@ic('kb', 'Outputs the internal knowledge base')
def ic_kb(arguments):
    print(formatting.comment('% Outputting internal KB:'))
    all_preds = set(current_context.knowledge.facts.keys()) | set(current_context.knowledge.rules.keys()) | set(current_context.knowledge.prim.keys())
    for pred in all_preds:
        print(formatting.comment('%') + " {} =>".format(pred))
        for db in (current_context.knowledge.facts, current_context.knowledge.rules):
            asserted = db.get(pred)
            if asserted:
                for id, clause in asserted.items():
                    print(formatting.comment('%')+"   {}".format(clause))
        primitive = current_context.knowledge.prim.get(pred)
        if primitive:
            for generator in primitive:
                print(formatting.comment('%')+"   <primitive> (bound to {})".format(generator.description))


@ic('help', 'Displays all available commands and their description')
def ic_help(arguments):
    print(formatting.comment('% Available commands:'))
    for cmd in interactive_commands.values():
        print(formatting.comment("% .{}: {}".format(cmd.command, cmd.description)))


@ic('ext', 'Displays a list of all available extensions, or display list of all predicates in an extension')
def ic_extensions(arguments):
    if not arguments:
        print(formatting.comment('% Available extensions:'))
        for ext in extensions.list_extensions():
            print(formatting.comment("% {}".format(ext.name)))
    else:
        for ext in extensions.list_extensions():
            if ext.name == arguments[0]:
                break
        else:
            raise judged.JudgedError("Unknown extensions '{}'".format(arguments[0]))
        print(formatting.comment("% Available predicates in {}:".format(arguments[0])))
        for pred in ext.predicates.values():
            print(formatting.comment("%")+" {}".format(pred.predicate))



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
    global current_context, args

    # set up shared options for all prover commands
    shared_options = argparse.ArgumentParser(add_help=False)
    shared_options.add_argument('file', metavar='FILE', type=argparse.FileType('r', encoding='utf-8'), nargs='*',
                         help='Input files to process in batch.')
    shared_options.add_argument('-i', '--import', default=False, action='store_true', dest='imports',
                         help='Imports the judged files before going to interactive mode.')
    shared_options.add_argument('-V', '--verbose', default=False, action='store_true',
                         help='Increases verbosity. Outputs each imported statement before doing it.')
    shared_options.add_argument('-v', '--verbose-questions', default=False, action='store_true',
                         help='Increases verbosity for all questions. Outputs each question before answering.')
    shared_options.add_argument('-d', '--debug', default=False, action='store_true',
                         help='Enables debugging output.')
    shared_options.add_argument('-e', '--extension', action='append', default=[], dest='extensions',
                         help='Names of python modules to import for extension loading.')

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

    judged.formatting.default_format_spec = args.format

    # determine debugger
    debugger = None
    if args.debug:
        debugger = ReportingDebugger()

    context_options = {
        'debugger': debugger
    }

    # load extension modules
    for extension in args.extensions:
        if args.verbose:
            print(formatting.comment("% loading extension module '{}'".format(extension)))
        try:
            ext = importlib.import_module(extension)
        except ImportError as e:
            print("Error: Could not load the extension module '{}', is the module loadable as a python module?".format(extension))
            if args.verbose:
                message = traceback.format_exc()
                print(textwrap.indent(message, '> '))
            options.exit(1)
        except extensions.ExtensionError as e:
            print("Error in extension: {}".format(e.message))
            options.exit(1)

    # construct context
    if args.type == 'deterministic':
        current_context = context.DeterministicContext(**context_options)
    elif args.type == 'exact':
        current_context = context.ExactContext(**context_options)
    elif args.type == 'montecarlo':
        current_context = context.MontecarloContext(number=args.number, approximate=args.approximate, **context_options)

    if args.file:
        batch(args.file)
        if args.imports:
            interactive()
    else:
        interactive()


if __name__ == '__main__':
    main()

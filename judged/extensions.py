import functools

import judged

__all__ = [
    'Extension',
    'list_extensions'
]


class ExtensionError(judged.JudgedError):
    """
    An error to indicate that the extension mechanism broke down.
    """
    pass


known_extensions = {}


def register_extension(ext):
    if ext.name in known_extensions:
        raise ExtensionError("Multiple extensions try to use the name '{}'".format(ext.name))
    known_extensions[ext.name] = ext


def list_extensions():
    return list(known_extensions.values())


class PredicateInfo:
    def __init__(self, name, arity, needs_context, function):
        self.name = name
        self.arity = arity
        self.needs_context = needs_context
        self.function = function

    @property
    def id(self):
        return "{}/{}".format(self.name, self.arity)

    def __repr__(self):
        return "PredicateInfo(name={}, arity={}, needs_context={}, function={})".format(self.name, self.arity, self.needs_context, self.function)


class Extension:
    def __init__(self, name):
        self.name = name
        self.predicates = {}
        self.setup_functions = []
        self.before_ask_functions = []
        self.after_ask_functions = []
        register_extension(self)

    def predicate(self, name, arity, needs_context=False):
        # create a registration function for the given parameters
        def predicate_registerer(function):
            # create an information piece for this predicate function
            info = PredicateInfo(name, arity, needs_context, function)
            if info.id in self.predicates:
                raise ExtensionError("Registering a second '{}' predicate in the '{}' extension".format(info.id, self.name))
            self.predicates[info.id] = info
            # return the old function
            return function
        return predicate_registerer

    def setup(self, f):
        self.setup_functions.append(f)

    def before_ask(self, f):
        self.before_ask_functions.append(f)

    def after_ask(self, f):
        self.after_ask_functions.append(f)

    def _do_before_ask(self, context):
        for f in self.before_ask_functions:
            f(context)

    def _do_after_ask(self, context):
        for f in self.after_ask_functions:
            f(context)

    def _do_setup(self, context, parameters):
        for f in self.setup_functions:
            f(context, parameters)

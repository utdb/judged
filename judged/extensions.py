"""
Extensions module with developer-friendly interface to the extension mechanics
available in JudgeD.
"""

import functools

import judged


__all__ = [
    'Extension',
    'ExtensionError',
    'list_extensions'
]


class ExtensionError(judged.JudgedError):
    """
    An error to indicate that the extension mechanism broke down.
    """
    pass


known_extensions = {}


def register_extension(ext):
    """Helper function to register a new extension."""
    if ext.name in known_extensions:
        raise ExtensionError("Multiple extensions try to use the name '{}'".format(ext.name))
    known_extensions[ext.name] = ext


def list_extensions():
    """Returns a list of all registered extensions."""
    return list(known_extensions.values())


class PredicateInfo:
    """Plain object to combine information on an extension's predicate."""
    def __init__(self, name, arity, needs_context, function):
        self.predicate = judged.Predicate(name, arity)
        self.needs_context = needs_context
        self.function = function

    @property
    def id(self):
        return self.predicate.id


class Extension:
    """
    The Extension class is instantiated to create an extensions.

    Once created, predicates can be registered on the extension via the use of
    the `predicate` decorator:

    >>> ext = Extension(__name__)
    >>> @ext.predicte("name", 2)
    ... def name(pred, a, b):
    ...     pass

    It is also possible to register one or more setup functions through the
    `setup` decorator, and to register functions to be run before and after an
    ask on the context with `before_ask` and `after_ask`.
    """
    def __init__(self, name):
        self.name = name
        self.predicates = {}
        self.setup_functions = []
        self.before_ask_functions = []
        self.after_ask_functions = []
        register_extension(self)

    def __str__(self):
        return "<judged.extensions.Extension '{}'>".format(self.name)

    def predicate(self, name, arity, needs_context=False):
        """Predicate decorator to register a predicate with the extension.

        The predicate decorator requires that the predicate's name and arity are
        given, and allows an optional needs_context parameter to indicate that
        the predicate function requires the program context when invoked.

        A predicate function is given the actual predicate instance as first
        argument, followed by the terms of the literal. If needs_context was
        given, the current context will be givan as an additional, final
        argument.
        """
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

    def _find_predicate(self, full_name):
        name, sep, arity = full_name.rpartition('/')
        if name and arity:
            identifier = full_name
            return self.predicates.get(identifier)
        else:
            name = name or arity
            candidates = []
            for p in self.predicates.values():
                if p.predicate.name == name:
                    candidates.append(p)
            if len(candidates) == 0:
                return None
            elif len(candidates) == 1:
                return candidates[0]
            else:
                raise ExtensionError("Multiple predicates known with name '{}' (i.e., {}), please qualify with arity".format(name, ', '.join("{}".format(p.predicate) for p in candidates)))

    def register_predicate(self, context, full_name, alias=None):
        if full_name is None:
            for pred in self.predicates.values():
                context.knowledge.add_primitive(pred.predicate, predicate_generator(pred), self.name + '.' + pred.id)
        else:
            pred = self._find_predicate(full_name)
            if not pred:
                raise ExtensionError("No predicate of the name '{}' is present in module '{}'".format(full_name, self.name))
            predicate = pred.predicate if not alias else judged.Predicate(alias, pred.predicate.arity)
            generator = predicate_generator(pred)
            context.knowledge.add_primitive(predicate, generator, self.name + '.' + pred.id)

    def setup(self, f):
        """Registers a function to run when the extensions is set up for use."""
        self.setup_functions.append(f)

    def before_ask(self, f):
        """Registers a function to run when an ask is starting."""
        self.before_ask_functions.append(f)

    def after_ask(self, f):
        """Registers a function to run when an as is finished."""
        self.after_ask_functions.append(f)

    def _do_before_ask(self, context):
        for f in self.before_ask_functions:
            f(context)

    def _do_after_ask(self, context):
        for f in self.after_ask_functions:
            f(context)

    def _do_setup(self, context, parameters):
        for f in self.setup_functions:
            f(context, **parameters)


def predicate_generator(info):
    if info.needs_context:
        @functools.wraps(info.function)
        def predicate_proxy(literal, context):
            context_info = {
                'context': context
            }
            yield from info.function(literal.pred, *literal.terms, **context_info)
    else:
        @functools.wraps(info.function)
        def predicate_proxy(literal, context):
            yield from info.function(literal.pred, *literal.terms)
    return predicate_proxy

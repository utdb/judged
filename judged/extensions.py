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
        self.predicate = judged.Predicate(name, arity)
        self.needs_context = needs_context
        self.function = function

    @property
    def id(self):
        return self.predicate.id

    def __repr__(self):
        return "PredicateInfo(predicate={}, needs_context={}, function={})".format(self.predicate, self.needs_context, self.function)


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

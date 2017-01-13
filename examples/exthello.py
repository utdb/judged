from judged import Constant, Literal, Predicate, Clause
from judged.extensions import Extension, ExtensionError

ext = Extension(__name__)


# the thing we are helloing
the_thing = ''


@ext.predicate('say', 2)
def say(pred, a, b):
    # For very simple predicates we can ignore the terms we are given, judged
    # will attempt unification after receiving the clauses anyway.
    head = Literal(pred, [Constant.string('hello'), Constant.string(the_thing)])
    body = []
    yield Clause(head, body)


@ext.predicate('complex', 1, needs_context=True)
def complex(pred, a, *, context=None):
    # More complex or involved predicates can request that they are given the
    # query context. This makes it possible to set up a query-level cache in an
    # @ext.before_ask function, use the cache in the predicates, and tear down
    # the cache in an #ext.after_ask function.
    yield Clause(Literal(pred, [Constant.number(1337)]))


@ext.setup
def init(context, thing="(default)", **rest):
    """Initialise the exthello extension, which takes one parameter 'thing'.

    The other parameters are ignored, and an error is thrown if we get them.
    """
    if rest:
        raise ExtensionError("exthello only supports the 'thing' parameter")

    # We store the configuration globally in this module, which works well
    # enough for most use-cases.
    global the_thing
    the_thing = thing


@ext.before_ask
def prepare_something(context):
    print("exthello sees the start of a query!")


@ext.after_ask
def clear_out_mess(context):
    print("exthello sees the end of a query!")

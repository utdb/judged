import sqlite3

import judged
from judged.external import SqlBindings
from judged.external import eager_loading, conservative_loading, custom_strategy


def preload_for_predicates(literal):
    """
    A custom caching strategy.

    The idea is that a query for a specific subject with some predicate is often
    done in the context of a query that retrieves all subjects with that
    predicate. Alternatively, the literal is passed through to the caching
    mechanism.
    """
    if literal.terms[1].is_const():
        new_terms = [judged.make_fresh_var(), literal.terms[1], literal.terms[2]]
        return judged.Literal(literal.pred, new_terms)
    else:
        return literal


def initialize(config, kb, actions):
    """
    Module entry point to initialize for the given knowledge base and prover.
    """
    # default configuration
    defaults = {
        'database': 'examples/demosql.sqlite'
    }
    defaults.update(config)

    # connect to the database
    connection = sqlite3.connect(defaults['database'])

    # Construct bindings
    bindings = SqlBindings(connection, kb)

    bindings.simple(('triple',3), 'triples', ['subject', 'predicate', 'object'],
            caching=custom_strategy(preload_for_predicates))

from functools import wraps

import judged


def sql_simple(connection, predicate, table, columns):
    #TODO: Type handling (in input and output)
    """
    Factory function to calculate the actual predicate function.
    """
    def native(literal, prover):
        """
        The actual predicate function.
        """
        # bookkeeping data
        tests = ['1=1']
        constants = []
        variables = {}

        # build up query by inspecting literal terms
        for i,term in enumerate(literal.terms):
            col = columns[i]
            if term.is_const():
                tests.append("{} = ?".format(col))
                constants.append(term.data or term.name)
            else:
                if term not in variables:
                    variables[term] = col
                else:
                    tests.append("{} = {}".format(variables[term], col))

        # construct query by patching together components
        query = "SELECT {fields} FROM {table} WHERE {tests}".format(
            fields=', '.join(columns),
            table=table,
            tests=' AND '.join(tests))

        # execute query and build result clauses
        for row in connection.execute(query, constants):
            values = []
            for v in row:
                values.append(judged.Constant(str(v), kind='string', data=v))
            head = judged.Literal(predicate, values)
            yield judged.Clause(head)
    return native


class SqlBindings:
    def __init__(self, connection, kb):
        self.connection = connection
        self.kb = kb

    def simple(self, predicate, table, columns, caching=None):
        pred = judged.Predicate(*predicate)
        func = sql_simple(self.connection, pred, table, columns)
        if caching is not None:
            func = caching(func)
        self.kb.add_primitive(pred, func)


def _caching_decorator(transform_literal):
    sentinel = object()
    def cache_wrapper(f):
        @wraps(f)
        def wrapped(original_literal, prover):
            literal = transform_literal(original_literal)
            if literal is None:
                yield from f(literal, prover)
                return
            cache = prover.cache
            key = literal.tag()
            result = cache.get(key, sentinel)
            if result is sentinel:
                result = list(f(literal, prover))
                cache[key] = result
            yield from result
        return wrapped
    return cache_wrapper


def apply_caching(strategy, source):
    return strategy(source)


def custom_strategy(literal_transformer):
    return _caching_decorator(literal_transformer)


def conservative_loading():
    return _caching_decorator(lambda lit: lit)


def eager_loading(consider_free=None):
    if consider_free is None:
        def transform_literal(literal):
            new_terms = [judged.make_fresh_var() for t in literal.terms]
            return judged.Literal(literal.pred, new_terms)
    else:
        def transform_literal(literal):
            new_terms = [judged.make_fresh_var() if i in consider_free else t for i,t in enumerate(literal.terms)]
            return judged.Literal(literal.pred, new_terms)

    return _caching_decorator(transform_literal)


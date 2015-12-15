import datalog
from datalog.external import apply_caching, eager_loading


def data(literal, prover):
    """
    Generator for external data.
    """
    for i in range(5):
        c = datalog.Constant(str(i), kind='number', data=i)
        head = datalog.Literal(datalog.Predicate('data', 2), [c, c])
        yield datalog.Clause(head)


def more_data(literal, prover):
    """
    Generator for more external data.
    """
    for i in range(50):
        c = datalog.Constant(str(i), kind='number', data=i)
        head = datalog.Literal(datalog.Predicate('more_data', 1), [c, c])
        yield datalog.Clause(head)



def initialize(config, kb, actions):
    """
    Initialization function to add primitive predicate to knowledge base.
    """
    kb.add_primitive(datalog.Predicate('data', 2), data)
    kb.add_primitive(datalog.Predicate('more_data', 1), apply_caching(eager_loading(), more_data))

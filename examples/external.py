import judged
from judged.external import apply_caching, eager_loading


def data(literal, prover):
    """
    Generator for external data.
    """
    for i in range(5):
        c = judged.Constant(str(i), kind='number', data=i)
        head = judged.Literal(judged.Predicate('data', 2), [c, c])
        yield judged.Clause(head)


def more_data(literal, prover):
    """
    Generator for more external data.
    """
    for i in range(50):
        c = judged.Constant(str(i), kind='number', data=i)
        head = judged.Literal(judged.Predicate('more_data', 1), [c, c])
        yield judged.Clause(head)



def initialize(config, kb, actions):
    """
    Initialization function to add primitive predicate to knowledge base.
    """
    kb.add_primitive(judged.Predicate('data', 2), data)
    kb.add_primitive(judged.Predicate('more_data', 1), apply_caching(eager_loading(), more_data))

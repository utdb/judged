from datalog.interned import InternalizeMeta
from operator import attrgetter

class Node(metaclass=InternalizeMeta):
    def __init__(self, root, high, low):
        self._root = root
        self._high = high
        self._low = low

    def __repr__(self):
        return self.__class__.__name__ + "(root={}, high={}, low={})".format(self.root, self.high, self.low)

    root = property(attrgetter('_root'))
    high = property(attrgetter('_high'))
    low = property(attrgetter('_low'))

ZERO = Node(-1, None, None)
ONE = Node(-2, None, None)


def _node(root, high, low):
    if high is low:
        return high
    else:
        return Node(root, high, low)

def _neg(node):
    if node is ZERO:
        # ~0 = 1
        return ONE
    elif node is ONE:
        # ~1 = 0
        return ZERO
    else:
        # ~(f -> g,h) = f -> ~g, ~h
        return _node(node.root, _neg(node.high), _neg(node.low))


def _ite(f, g, h):
    """
    The If-Then-Else operator `f -> g,h` is defined as `(f & g) | (~f & h)`.

    This function applies the operator to already represented nodes.
    """
    # f -> 1, 0 = f
    if g is ONE and h is ZERO:
        return f
    # f -> 0, 1 = ~f
    elif g is ZERO and h is ONE:
        return _neg(f)
    # 1 -> g, h = g
    elif f is ONE:
        return g
    # 0 -> g, h = h
    elif f is ZERO:
        return h
    # f -> g, g = g
    elif g is h:
        return g
    # f -> g, h = x -> (fx -> gx, hx), (fx' -> gx', hx')
    else:
        # Order variables (to obtain Ordered BDD), skip ZERO and ONE' magic
        # numbers -1 and -2.
        root = min(n.root for n in (f, g, h) if not n.root < 0)
        f1, g1, h1 = [_restrict(n, {root: ONE}) for n in (f, g, h)]
        f0, g0, h0 = [_restrict(n, {root: ZERO}) for n in (f, g, h)]
        return _node(root, _ite(f1, g1, h1), _ite(f0, g0, h0))


def _restrict(node, point):
    # shortcut constants
    if node in (ZERO, ONE):
        return node

    if node.root in point:
        # this node is restricted
        child = {ONE: node.high, ZERO: node.low}[point[node.root]]
        return _restrict(child, point)
    else:
        # this node is not restricted, recurse through
        return _node(node.root, _restrict(node.high, point), _restrict(node.low, point))


# FIXME: Should these be collapsed into _node?
class BDD:
    """
    Wrapper class around _node that handles programmer-friendly interaction.
    """
    def __init__(self, node):
        self.node = node

    def restrict(self, point):
        return BDD(_restrict(self.node))

    def is_zero(self):
        return self.node == ZERO

    def is_one(self):
        return self.node == ONE

    def __eq__(self, other):
        if other is None:
            return False
        try:
            return self.node == other.node
        except AttributeError:
            return False

    def __invert__(self):
        # ~f <=> _neg(f)
        return BDD(_neg(self.node))

    def __or__(self, other):
        # f | g <=> _ite(f, 1, g)
        return BDD(_ite(self.node, ONE, other.node))

    def __and__(self, other):
        # f & g <=> _ite(f, g, 0)
        return BDD(_ite(self.node, other.node, ZERO))

    def __xor__(self, other):
        # f ^ g <=> _ite(f, g', g)
        return BDD(_ite(self.node, _neg(other.node), other.node))

    def to_dot(self):
        seen = set()
        def dotter(node):
            if node in seen:
                return ''
            seen.add(node)
            if node is ONE:
                return "n{} [label=\"1\", shape=box];\n".format(id(node))
            elif node is ZERO:
                return "n{} [label=\"0\", shape=box];\n".format(id(node))
            else:
                name = str(variables[node.root]).replace('"', '\\"')
                result = ''
                result += "n{} [label=\"{}\"];\n".format(id(node), name)
                result += "n{} -> n{} [style=dotted];\n".format(id(node), id(node.low))
                result += "n{} -> n{};\n".format(id(node), id(node.high))
                result += dotter(node.low)
                result += dotter(node.high)
                return result
        return "digraph BDD {\n" + dotter(self.node) + "}"


def constant(val):
    if bool(val):
        return BDD(ONE)
    else:
        return BDD(ZERO)


variables = {}
variables_rev = {}

def variable(name):
    try:
        identifier = variables_rev[name]
    except KeyError:
        identifier = len(variables)
        variables[identifier] = name
        variables_rev[name] = identifier
    return BDD(_node(identifier, ONE, ZERO))

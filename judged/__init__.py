"""
The judged module.
"""

from judged import interned
from judged import worlds
from judged import formatting


__all__ = [
    'JudgedError', 'ParseError', 'TokenizeError',
    'Constant', 'Variable', 'Predicate', 'Literal', 'Clause'
]


class JudgedError(Exception):
    """
    Base error for all errors produced by judged.
    """
    def __init__(self, message, context=None):
        self.message = message
        self.context = context


class ParseError(JudgedError):
    """
    An error during the parsing of a judged source.
    """
    pass


class TokenizeError(ParseError):
    """
    An error during the tokenization phase of parsing a source.
    """
    pass


def constant_key(args, kwargs):
    if len(args) == 1:
        return (args[0], kwargs.get('kind', None))
    else:
        return args[:2]


class Constant(metaclass=interned.InternalizeMeta, key=constant_key):
    """
    Constant term.
    """
    def __init__(self, name, kind=None, data=None):
        self.data = data
        self.kind = kind
        self.name = name
        self.id = 'c$' + (kind if kind else '') + '$' + name

    def __str__(self):
        return format(self, 'plain')

    def __format__(self, format_spec):
        return formatting.constant(self, format_spec)

    def __repr__(self):
        return self.id

    def is_const(self):
        return True

    def tag(self, i, env):
        """A constant's tag is itself."""
        return self.id

    def subst(self, env):
        """Substitution of a constant retains the constant."""
        return self

    def shuffle(self, env):
        """No new variables are introduced to shuffle a constant."""
        pass

    def chase(self, env):
        """The chase of a constant is itself."""
        return self

    def unify(self, other, env):
        """Dispatch to perform constant unification."""
        return other.unify_const(self, env)

    def unify_const(self, const, env):
        """A constant does not unify with another constant."""
        return None

    def unify_var(self, var, env):
        """Let the variable sort out unification with a constant."""
        return var.unify_const(self, env)


class Variable(metaclass=interned.InternalizeMeta):
    """
    Variable term.
    """
    def __init__(self, name):
        self.name = name
        self.id = 'v' + name

    def __str__(self):
        return format(self, 'plain')

    def __format__(self, format_spec):
        return formatting.variable(self, format_spec)

    def __repr__(self):
        return self.id

    def is_const(self):
        return False

    def tag(self, i, env):
        """
        A variable's tag is the tag already present for it, or the tag term 'i'
        given to it by the tagging process.
        """
        result = env.get(self)
        if not result:
            result = 'v' + str(i)
            env[self] = result
        return result

    def subst(self, env):
        """
        Substitution of a variable replaces it with its replacement term, if no
        replacement term is present the variable remains.
        """
        term = env.get(self)
        if term:
            return term
        else:
            return self

    def shuffle(self, env):
        """
        Variables are shuffled by creating a 1-to-1 mapping of fresh variables.
        """
        if not env.get(self):
            env[self] = make_fresh_var()

    def chase(self, env):
        """
        A variable's chase follows every substitution until we end up with the
        final variable or constant at the end of the chain.
        """
        result = env.get(self)
        if result:
            return result.chase(env)
        else:
            return self

    def unify(self, other, env):
        """Dispatch to perform variable unification."""
        return other.unify_var(self, env)

    def unify_const(self, const, env):
        """
        A variable unifies with a constant by replacing all occurances of that
        variable with the constant.
        """
        env[self] = const
        return env

    def unify_var(self, var, env):
        """
        A variable unifies with another variable by replacing the occurances of
        the other variable by itself.
        """
        env[var] = self
        return env


def make_fresh_var():
    """
    Makes fresh variables that are guaranteed not to have been used before. This
    guarantee is given by automaticall incrementing the numeric identifier used
    to create a variable.
    """
    make_fresh_var.counter += 1
    return Variable('_' + str(make_fresh_var.counter))

make_fresh_var.counter = 0


class Predicate(metaclass=interned.InternalizeMeta):
    """
    A predicate with name and arity.
    """
    def __init__(self, name, arity):
        self.id = name + '/' + str(arity)
        self.name = name
        self.arity = arity

    def __str__(self):
        return format(self, 'plain')

    def __format__(self, format_spec):
        return formatting.predicate(self, format_spec)

    def __repr__(self):
        return self.id

def add_size(string):
    """Helper function for tag creation."""
    return str(len(string)) + ':' + string


class Literal:
    """
    A literal consists of a predicate and a list of terms. The literal
    behaves as a sequence with respect to it's terms. Additionally, it
    exposes the pred, id, and tag properties.
    """
    def __init__(self, pred, terms, polarity=True):
        self.pred = pred
        self.terms = terms
        self.polarity = polarity
        self._id = None
        self._tag = None

    def __str__(self):
        return format(self, 'plain')

    def __format__(self, format_spec):
        return formatting.literal(self, format_spec)

    def __getitem__(self, key):
        return self.terms[key]

    def __iter__(self):
        return iter(self.terms)

    def __len__(self):
        return len(self.terms)

    def __contains__(self, item):
        return item in self.terms

    def __eq__(self, other):
        try:
            return self.id == other.id
        except:
            return False

    def __hash__(self):
        return hash(self.id)

    @property
    def id(self):
        """Determines a unique id for the literal."""
        result = self._id
        if not result:
            polarity = '' if self.polarity else '~'
            result = polarity + add_size(self.pred.id)
            for t in self:
                result += add_size(t.id)
            self._id = result
        return result

    def tag(self):
        """
        Determines a tag for the literal. The tags of two literals are equal if
        the two literals are structurally the same.
        """
        result = self._tag
        if not result:
            env = dict()
            polarity = '' if self.polarity else '~'
            result = polarity + add_size(self.pred.id)
            for i in range(len(self)):
                result += add_size(self[i].tag(i, env))
            self._tag = result
        return result

    def subst(self, env):
        """Performs the substitution described in env on the literal."""
        if not env:
            return self

        terms = list(map(lambda t: t.subst(env), self.terms))
        return Literal(self.pred, terms, self.polarity)

    def shuffle(self, env=None):
        """
        Produces or updates an environment with shuffled variables for all
        variables present in the literal.
        """
        result = env if env is not None else dict()
        for t in self:
            t.shuffle(result)
        return result

    def rename(self):
        """
        Renames the literal such that all variables are replaced by fresh ones.
        """
        return self.subst(self.shuffle())

    def unify(self, other):
        """
        Unifies this literal with another. The result is either None or a
        substitution environment. Applying the substitution environment to both
        literals will result in two new literals that are structurally equal.
        """
        if self.pred != other.pred:
            return None

        env = dict()
        for i in range(self.pred.arity):
            term_i = self[i].chase(env)
            other_i = other[i].chase(env)

            if term_i != other_i:
                env = term_i.unify(other_i, env)
                if env is None:
                    return None
        return env

    def invert(self):
        """
        Returns a new literal with an inverted polarity.
        """
        return Literal(self.pred, self.terms, not self.polarity)

    def is_grounded(self):
        """
        Determines whether the literal is grounded or not.
        """
        return all(t.is_const() for t in self)


class Clause:
    """
    A judged clause consist of a head literal, zero or more body literals,
    zero or more delayed literals and a descriptive sentence. A clause without
    a body is called a 'fact', and a clause with a body is called a 'rule'.

    A clause can be instantiated without a body, in which case it will act as if
    it were instantiated with an empty body, i.e. it is a fact.

    The clause acts as a set with respect to the literals found in delayed and
    body.
    """
    def __init__(self, head, body=[], delayed=[], sentence=worlds.Top()):
        self.head = head
        self.body = body
        self.delayed = delayed
        self.sentence = sentence
        self._id = None

    def __str__(self):
        return format(self, 'plain')

    def __format__(self, format_spec):
        return formatting.clause(self, format_spec)

    def __iter__(self):
        yield from self.body
        yield from self.delayed

    def __len__(self):
        return len(self.body) + len(self.delayed)

    def __contains__(self, item):
        return item in self.body or item in self.delayed

    def __eq__(self, other):
        try:
            return self.id == other.id
        except:
            return False

    def __hash__(self):
        return hash(self.id)

    @property
    def id(self):
        """Determine a unique string representation."""
        result = self._id
        if not result:
            result = add_size(self.head.id)
            for lit in self.body:
                result += add_size(lit.id)
            result += '|'
            for lit in self.delayed:
                result += add_size(lit.id)
            result += '%' + add_size(repr(self.sentence))
            self._id = result
        return result

    def subst(self, env):
        """
        Substitution on a clause is done by applying the substitution to all
        literals used in the clause.
        """
        if not env:
            return self

        s = lambda t: t.subst(env)
        body = list(map(s, self.body))
        delayed = list(map(s, self.delayed))
        return Clause(self.head.subst(env), body, delayed, self.sentence)

    def rename(self):
        """
        Renames all variables in the clause. The head is ignored when
        determining the substitution environment because every variable in the
        head is also present in the body (under the assumption that the clause
        is safe).
        """
        env = dict()
        for lit in self:
            lit.shuffle(env)

        if not env:
            return self
        else:
            return self.subst(env)

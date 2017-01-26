"""
Module responsible for possible world and descriptive sentence handling.
"""

from judged import bdd
from judged import interned
from judged import formatting


class Sentence:
    def __format__(self, format_spec):
        return formatting.sentence(self, format_spec)

    def __repr__(self):
        return str(self)

    def create_bdd(self):
        raise NotImplementedError

    def labels(self):
        return set()

    def evaluate(self, checker):
        raise NotImplementedError

    def is_grounded(self):
        return True

    def subst(self, env):
        raise NotImplementedError


class Nary(Sentence):
    def __init__(self, *terms):
        self.terms = list(terms)

    def nary2string(self, opstr):
        if len(self.terms) == 1:
            return str(self.terms[0])
        terms = []
        for t in self.terms:
            terms.append(str(t))
        return '(' + (' ' + opstr + ' ').join(terms) + ')'

    def labels(self):
        return {e for t in self.terms for e in t.labels()}

    def is_grounded(self):
        return all(t.is_grounded() for t in self.terms)

    def subst(self, env):
        return type(self)(*[t.subst(env) for t in self.terms])


class Unary(Sentence):
    def __init__(self, sub):
        self.sub = sub

    def labels():
        return self.sub.labels()

    def is_grounded(self):
        return self.sub.is_grounded()

    def subst(self, env):
        return type(self)(self.sub.subst(env))


class Atom(Sentence, metaclass=interned.InternalizeMeta):
    def subst(self, env):
        return self


class Disjunction(Nary):
    def __str__(self):
        return self.nary2string("or")

    def create_bdd(self):
        res = bdd.constant(False)
        for s in self.terms:
            res = res | s.create_bdd()
        return res

    def evaluate(self, checker):
        for t in self.terms:
            if t.evaluate(checker) == True:
                return True
        return False

class Conjunction(Nary):
    def __str__(self):
        return self.nary2string("and")

    def create_bdd(self):
        res = bdd.constant(True)
        for s in self.terms:
            res = res & s.create_bdd()
        return res

    def evaluate(self, checker):
        for t in self.terms:
            if t.evaluate(checker) == False:
                return False
        return True


class Negation(Unary):
    def __str__(self):
        return "not {!s}".format(self.sub)

    def create_bdd(self):
        return ~ (self.sub.create_bdd())

    def evaluate(self, checker):
        return not self.sub.evaluate(checker)

    def labels(self):
        return self.sub.labels()


class Label(Atom):
    def __init__(self, partitioning, part):
        self.partitioning = partitioning
        self.part = part

    def __str__(self):
        return "{}={}".format(self.partitioning, self.part)

    def create_bdd(self):
        return label_bdd_var(self.partitioning, self.part)

    def labels(self):
        return set([(self.partitioning, self.part)])

    def evaluate(self, checker):
        return checker(self.partitioning, self.part)

    def is_grounded(self):
        return self.partitioning.is_grounded() and self.part.is_grounded()

    def subst(self, env):
        return type(self)(self.partitioning.subst(env), self.part.subst(env))


class LabelFragment(metaclass=interned.InternalizeMeta):
    @staticmethod
    def add_size(s):
        return str(len(s)) + ':' + s

    def is_grounded(self):
        raise NotImplementedError

    def variables(self):
        return []


class LabelConstant(LabelFragment):
    def __init__(self, constant):
        self.constant = constant

    def __str__(self):
        return str(self.constant)

    def __repr__(self):
        return "<LabelConstant '{}'>".format(self.constant)

    def is_grounded(self):
        return True

    def subst(self, env):
        return self

    def tag(self):
        return self.add_size(str(self.constant))


class LabelFunction(LabelFragment):
    def __init__(self, name, terms):
        self.name = name
        self.terms = terms
        self._tag = None

    def __str__(self):
        return self.name + '(' +  ', '.join(str(t) for t in self.terms) + ')'

    def __repr__(self):
        return "<LabelFunction {}>".format(self)

    def is_grounded(self):
        return all(t.is_const() for t in self.terms)

    def variables(self):
        return [t for t in self.terms if not t.is_const()]

    def subst(self, env):
        if not env:
            return self

        terms = list(map(lambda t: t.subst(env), self.terms))
        return LabelFunction(self.name, tuple(terms))

    def tag(self):
        result = self._tag
        if not result:
            result = self.add_size(self.name)
            for i in range(len(self.terms)):
                result += self.add_size(self.terms[i].id)
            self._tag = result
        return result


class Top(Atom):
    def __str__(self):
        return "true"

    def create_bdd(self):
        return bdd.constant(True)

    def evaluate(self, checker):
        return True


class Bottom(Atom):
    def __str__(self):
        return "false"

    def create_bdd(self):
        return bdd.constant(False)

    def evaluate(self, checker):
        return False


def label_bdd_var(partition, part):
    """ helper function to ensure bddvars have same name everywhere """
    return bdd.variable(partition.tag() + '_' + part.tag())


def exclusion_matrix(partitions, kb):
    """
    Generates exclusion bdd's. So if xN has domain var[1,2] the following
    exclusion is generated: (x1 and not x2) or (x2 and not x1)
    """
    excl = None
    for key in partitions:
        group = kb.parts(key)
        if len(group) > 1:
            excl_sub = None
            excl_subsub = None
            for id in group:
                excl_subsub = label_bdd_var(key, id)
                for idnot in group:
                    if id != idnot:
                        excl_subsub = excl_subsub & ~ label_bdd_var(key, idnot)
                if excl_sub == None:
                    excl_sub = excl_subsub
                else:
                    excl_sub = excl_sub | excl_subsub
            if excl == None:
                excl = excl_sub
            else:
                excl = excl & excl_sub
    return excl

def equivalent(l, r, kb):
    """
    Determines if a descriptive sentence is equivalent to another, given the
    mutual exclusions from the given knowledge base.
    """
    assert l.is_grounded() and r.is_grounded(), "cannot compare ungrounded sentences"

    lbdd = l.create_bdd()
    rbdd = r.create_bdd()

    excl = exclusion_matrix({t[0] for t in (l.labels() | r.labels())}, kb)
    if excl is not None:
        lbdd = lbdd & excl
        rbdd = rbdd & excl

    return lbdd == rbdd

def falsehood(s, kb):
    """
    Determines if a world is a contradiction, i.e., if it can only exist
    through a violation of a mutually exclusive labelling.
    """
    sbdd = s.create_bdd()

    excl = exclusion_matrix({t[0] for t in s.labels()}, kb)
    if excl is not None:
        sbdd = sbdd & excl

    return sbdd.is_zero()

def labels(s):
    return s.labels()

def evaluate(s, checker):
    return s.evaluate(checker)

def is_grounded(s):
    return s.is_grounded()

def subst(s, env):
    return s.subst(env)

def conjunct(*terms):
    used = {t for t in terms if t != Top()}
    if len(used) == 0:
        return Top()
    elif len(used) == 1:
        return used.pop()
    else:
        return Conjunction(*used)

def disjunct(*terms):
    used = {t for t in terms if t != Bottom()}
    if len(used) == 0:
        return Bottom()
    elif len(used) == 1:
        return used.pop()
    else:
        return Disjunction(*used)

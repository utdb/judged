"""
Module responsible for possible world and descriptive sentence handling.
"""

from datalog import interned
from datalog import formatting


class Sentence:
    def __format__(self, format_spec):
        return formatting.sentence(self, format_spec)

    def __repr__(self):
        return str(self, 'plain')


class Binary(Sentence):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class Unary(Sentence):
    def __init__(self, sub):
        self.sub = sub


class Atom(Sentence, metaclass=interned.InternalizeMeta):
    pass


class Disjunction(Binary):
    def __str__(self):
        return "({!s} or {!s})".format(self.left, self.right)


class Conjunction(Binary):
    def __str__(self):
        return "({!s} and {!s})".format(self.left, self.right)


class Negation(Unary):
    def __str__(self):
        return "not {!s}".format(self.sub)


class Label(Atom):
    def __init__(self, partitioning, part):
        self.partitioning = partitioning
        self.part = part

    def __str__(self):
        return "{}={}".format(self.partitioning, self.part)


class Top(Atom):
    def __str__(self):
        return "true"


class Bottom(Atom):
    def __str__(self):
        return "false"

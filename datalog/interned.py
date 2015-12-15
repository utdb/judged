"""
This module allows the creation of internalized classes. An internalized class
has only a single instance for each key used in its instantiation, allowing
very fast equality tests and hashing.

This implementation is based on a metaclass approach to prevent instancing of
already interned values.

A contrived example is:

>>> class Foo(metaclass=InternalizeMeta):
>>>    def __init__(self, name):
>>>        self.name = name
>>> Foo("test") == Foo("test")
True
"""

import weakref


class Interned:
    """Mixin to apply correct equality and hashing for interned instances."""
    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __hash__(self):
        return id(self)


class InternalizeMeta(type):
    """
    Metaclass to create the necessary plumbing to all easy internalization on
    classes. This modifies the instance creation to only create a single
    instance per key. The key is determined by the key function stored in
    cls._key.

    Note that the key function is can be overridden in class definitions by
    given the key keyword parameter as a class argument. The key function
    receives two arguments: a sequence of paramters, and a dict of keyword
    parameters.
    """
    def __new__(cls, name, bases, namespace, **kwargs):
        """Adds Interned as a mixin to provide fast equality and hashing."""
        interned_bases = bases + (Interned,)
        result = type.__new__(cls, name, interned_bases, namespace)
        return result

    def __init__(cls, name, bases, namespace, key=lambda args, kwargs: args):
        cls._key = key
        cls._lookup = weakref.WeakValueDictionary()

    def __call__(cls, *args, **kwargs):
        """
        Determines the key from the construction arguments provided, and tests
        the class lookup dictionary for an existing instance. If no instance is
        found the normal instance creation process is invoked and the instance
        is internalized afterwards.
        """
        key = cls._key(args, kwargs)
        result = cls._lookup.get(key)
        if not result:
            result = type.__call__(cls, *args, **kwargs)
            cls._lookup[key] = result
        return result



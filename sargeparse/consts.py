import argparse


def _sentinel_factory(name):
    cls = type(name, (object,), {})
    cls.__repr__ = (lambda self: '<sargeparse.{}>'.format(name))
    cls.__add__ = (lambda self, other: other)
    cls.__radd__ = cls.__add__
    return cls()


unset = _sentinel_factory('unset')

suppress = argparse.SUPPRESS
remainder = argparse.REMAINDER

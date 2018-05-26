import argparse


def _sentinel_factory(name):
    cls = type(name, (object,), {})
    cls.__repr__ = (lambda self: '<sargeparse.{}>'.format(name))
    return cls()


unset = _sentinel_factory('unset')

suppress = argparse.SUPPRESS
remainder = argparse.REMAINDER

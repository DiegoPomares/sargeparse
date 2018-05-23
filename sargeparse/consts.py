import argparse


def _sentinel_factory(name):
    cls = type(name, (object,), {})
    cls.__repr__ = (lambda self: '<sargeparse.{}>'.format(name))
    return cls()


isset = _sentinel_factory('isset')
unset = _sentinel_factory('unset')
eval_true = _sentinel_factory('eval_true')
eval_false = _sentinel_factory('eval_false')

suppress = argparse.SUPPRESS
remainder = argparse.REMAINDER

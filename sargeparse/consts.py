import argparse


def _sentinel_factory(name):
    class Meta(type):
        def __new__(mcs, _name, bases, namespace):
            namespace['__qualname__'] = name
            return type.__new__(mcs, name, bases, namespace)

    class Sentinel(metaclass=Meta):
        def __init__(self, value=None):
            self.value = value
            super().__init__()

        def __repr__(self):
            return '<sargeparse.{}>'.format(name)

        def __call__(self, value):
            return Sentinel(value)

        # Add and radd were added because argparse uses the default value as the initial value
        # when action='count', instead of 0
        def __add__(self, other):
            return other

        def __radd__(self, other):
            return other

        def __eq__(self, other):
            return isinstance(other, type(self))

    return Sentinel()


unset = _sentinel_factory('unset')
stop = _sentinel_factory('stop')
die = _sentinel_factory('die')

suppress = argparse.SUPPRESS
remainder = argparse.REMAINDER

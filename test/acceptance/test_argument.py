# pylint: disable=redefined-outer-name
import sys
import shlex

from collections import ChainMap

import sargeparse


def test_int_type_no_nargs():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
                'type': int,
            }
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test --arg 10')

    args = parser.parse()

    assert args == ChainMap(
        {},
        {
            'arg': 10,
        },
        {},
        {},
        {},
        {
            'arg': sargeparse.unset,
        },
    )


def test_int_type_one_nargs():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
                'nargs': 1,
                'type': int,
            }
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test --arg 10')

    args = parser.parse()

    assert args == ChainMap(
        {},
        {
            'arg': [10],
        },
        {},
        {},
        {},
        {
            'arg': sargeparse.unset,
        },
    )


def test_int_type_many_nargs():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
                'nargs': 2,
                'default': [100, 200],
                'type': int,
            }
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test --arg 10 20')

    args = parser.parse()

    assert args == ChainMap(
        {},
        {
            'arg': [10, 20],
        },
        {},
        {},
        {},
        {
            'arg': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test')

    args = parser.parse()

    assert args == ChainMap(
        {},
        {},
        {},
        {},
        {
            'arg': [100, 200],
        },
        {
            'arg': sargeparse.unset,
        },
    )


def test_int_type_remainder():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
                'nargs': sargeparse.remainder,
                'default': [100, 200],
                'type': int,
            }
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test --arg 10 20')

    args = parser.parse()

    assert args == ChainMap(
        {},
        {
            'arg': [10, 20],
        },
        {},
        {},
        {},
        {
            'arg': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test')

    args = parser.parse()

    assert args == ChainMap(
        {},
        {},
        {},
        {},
        {
            'arg': [100, 200],
        },
        {
            'arg': sargeparse.unset,
        },
    )


def test_list_default_no_nargs():
    def type_fn(value):
        if isinstance(value, str):
            return int(value) * 10

        return 10

    definition = {
        'arguments': [
            {
                'names': ['--arg'],
                'default': [1, 2],
                'type': type_fn,
            }
        ],
    }

    parser = sargeparse.Sarge(definition)

    sys.argv = shlex.split('test')
    args = parser.parse()

    assert args == ChainMap(
        {},
        {
            'arg': 10,
        },
        {},
        {},
        {},
        {
            'arg': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test --arg 3')
    args = parser.parse()

    assert args == ChainMap(
        {},
        {
            'arg': 30,
        },
        {},
        {},
        {},
        {
            'arg': sargeparse.unset,
        },
    )

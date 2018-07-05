# pylint: disable=redefined-outer-name
import sys
import re
from collections import ChainMap

import pytest

import sargeparse


def test_non_callable_read_config():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
            }
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = ['test']

    with pytest.raises(TypeError) as ex:
        parser.parse(read_config=1)
    assert 'not callable' in str(ex)


def test_non_dict_return_from_read_config():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
            }
        ],
    }

    def read_config(_args):
        return 1

    parser = sargeparse.Sarge(definition)
    sys.argv = ['test']

    with pytest.raises(TypeError) as ex:
        parser.parse(read_config=read_config)
    assert re.search(r'returned a.*class.*int.*when.*dict.*None.*was expected', str(ex))


def test_read_config_returns_none():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
            }
        ],
    }

    def read_config(args):
        args.configuration['extra'] = 1

    parser = sargeparse.Sarge(definition)
    sys.argv = ['test']

    args = parser.parse(read_config=read_config)
    assert args == ChainMap(
        {},
        {},
        {},
        {},
        {
            'extra': 1,

        },
        {
            'arg': sargeparse.unset,
        },
    )

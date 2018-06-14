# pylint: disable=redefined-outer-name
import sys
import shlex

import pytest

import sargeparse


def test_invalid_config_path():
    definition = {
        'arguments': [
            {
                'names': ['--arg'],
            }
        ],
    }

    sys.argv = shlex.split('test')

    for path in (1, [], {}, [1], ['arg', 0]):
        definition['arguments'][0]['config_path'] = path
        with pytest.raises(TypeError) as ex:
            sargeparse.Sarge(definition)

        assert 'can only be <str> or <list of str>' in str(ex)

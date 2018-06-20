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


def test_no_names():
    definition = {
        'arguments': [
            {
                'help': 'ARGUMENT',
            }
        ],
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert 'missing or invalid' in str(ex)


def test_positional_argument_with_dest():
    definition = {
        'arguments': [
            {
                'names': ['arg'],
                'dest': 'argument',
            }
        ],
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert "Positional arguments cannot have a 'dest'" in str(ex)


def test_global_positional_argument():
    definition = {
        'arguments': [
            {
                'names': ['arg'],
                'global': True,
            }
        ],
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert "Positional arguments cannot be 'global'" in str(ex)


def test_global_subcommand_argument():
    definition = {
        'subcommands': [
            {
                'name': 'sub',
                'arguments': [
                    {
                        'names': ['arg'],
                        'global': True,
                    }
                ],
            },
        ],
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert "Subcommands' arguments cannot be 'global'" in str(ex)

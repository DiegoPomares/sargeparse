# pylint: disable=redefined-outer-name
import os
import sys
import shlex

from collections import ChainMap

import pytest

import sargeparse


@pytest.fixture
def sarge():
    return sargeparse.Sarge({})


def test_full_ok(caplog):

    parser = sargeparse.Sarge({
        'description': 'MAIN_DESCRIPTION',
        'epilog': 'MAIN_EPILOG',
        'callback': 'fn_main',
        'arguments': [
            {
                'names': ['--debug'],
                'action': 'store_true',
                'default': False,
                'global': True,
                'envvar': 'DEBUG',
            },
            {
                'names': ['-x'],
                'action': 'store_true',
                'default': False,
                'mutex_group': 1,
                'required': False,
                'group': 'X or Y',
            },
            {
                'names': ['-y'],
                'help': 'Yes!',
                'action': 'store_true',
                'default': False,
                'mutex_group': 1,
                'required': False,
                'group': 'X or Y',
            },
        ],
        'group_descriptions': {
            'X or Y': 'just a mutex group',
        },
        'defaults': {
            'extra': 'EXTRA_ARG',
        }
    })

    parser.add_arguments({
        'names': ['-a', '--arg'],
        'help': 'ARG_HELP',
        'default': 'argdef',
    }, {
        'names': ['-b', '--barg'],
        'help': 'BARG_HELP',
        'default': 'bargdef',
        'config_path': 'args/barg',
    })

    parser.add_subcommands({
        'name': 'run',
        'help': 'just a subcommand',
        'callback': 'fn_run',
        'arguments': [
            {
                'names': ['--flag'],
                'default': 'flagdef',
            },
            {
                'names': ['--boss'],
                'help': "Who's the boss?",
                'envvar': 'BOSS',
                'config_path': 'boss',
            }
        ],
    })

    def get_config(_args):
        return {
            'boss': 'configboss',
            'args': {
                'barg': 'configbarg'
            }
        }

    sys.argv = shlex.split('test -y run --flag "flag cli"')
    os.environ['BOSS'] = 'ENVBOSS'

    args = parser.parse(read_config=get_config)

    assert args == ChainMap(
        {},
        {
            'flag': 'flag cli',
            'y': True,
        },
        {
            'boss': 'ENVBOSS',
        },
        {
            'barg': 'configbarg',
            'boss': 'configboss',
        },
        {
            'arg': 'argdef',
            'barg': 'bargdef',
            'debug': False,
            'extra': 'EXTRA_ARG',
            'flag': 'flagdef',
            'x': False,
            'y': False,
        },
        {
            'arg': sargeparse.unset,
            'barg': sargeparse.unset,
            'boss': sargeparse.unset,
            'debug': sargeparse.unset,
            'flag': sargeparse.unset,
            'x': sargeparse.unset,
            'y': sargeparse.unset,
        }
    )

    for param in ['debug', 'x', 'flag']:
        assert "Missing 'help' in {}".format(param) in caplog.text

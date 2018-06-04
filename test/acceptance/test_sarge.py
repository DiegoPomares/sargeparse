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

    assert args.callbacks == ['fn_main', 'fn_run']

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


def test_envvar_default_config_same_name_many_subcommands():

    parser = sargeparse.Sarge({})

    parser.add_subcommands({
        'name': 'suba',
        'arguments': [
            {
                'names': ['--arg1'],
                'envvar': 'VARA'
            },
            {
                'names': ['--arg2'],
                'default': '2A'
            },
            {
                'names': ['--arg3'],
                'config_path': 'confA'
            },
        ],
    }, {
        'name': 'subb',
        'arguments': [
            {
                'names': ['--arg1'],
                'envvar': 'VARB'
            },
            {
                'names': ['--arg2'],
                'default': '2B'
            },
            {
                'names': ['--arg3'],
                'config_path': 'confB'
            },
        ],
    })

    def get_config(_args):
        return {
            'confA': '3A',
            'confB': '3B',
        }

    sys.argv = shlex.split('test suba')
    os.environ['VARA'] = '1A'
    os.environ['VARB'] = '1B'

    args = parser.parse(read_config=get_config)

    assert args == ChainMap(
        {},
        {},
        {
            'arg1': '1A',
        },
        {
            'arg3': '3A',
        },
        {
            'arg2': '2A',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
        }
    )


def test_callback_dispatch():

    obj_main = {
        'last': True
    }

    obj_sub = {
        'last': False,
        'value': 1
    }

    def cb_main(ctx):
        assert ctx.last == ctx.obj['last']

        if ctx.last:
            assert ctx.values['arg1'] == 'A1'
            assert ctx.values['arg2'] == sargeparse.unset

        else:
            assert ctx.obj['value'] == 1
            ctx.obj['value'] = 2
            ctx.values['arg2'] = 'A2'

    def cb_sub(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.values['arg1'] == 'A1'
        assert ctx.values['arg2'] == 'A2'

    parser = sargeparse.Sarge({
        'callback': cb_main,
        'arguments': [
            {
                'names': ['--arg1'],
                'default': 'A1',
            },
            {
                'names': ['--arg2'],
            },
        ],
        'subcommands': [
            {
                'name': 'sub',
                'callback': cb_sub,
            }
        ]
    })

    sys.argv = shlex.split('test')
    args = parser.parse()
    assert args.callbacks == [cb_main]
    args.dispatch(obj=obj_main)
    assert args == ChainMap(
        {},
        {},
        {},
        {},
        {
            'arg1': 'A1'
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test sub')
    args = parser.parse()
    assert args.callbacks == [cb_main, cb_sub]
    args.dispatch(obj=obj_sub)
    assert args == ChainMap(
        {
            'arg2': 'A2'
        },
        {},
        {},
        {},
        {
            'arg1': 'A1'
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
        },
    )

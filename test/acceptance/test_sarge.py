# pylint: disable=redefined-outer-name
import os
import sys
import shlex
import re

from collections import ChainMap

import pytest

import sargeparse


@pytest.fixture
def sarge():
    return sargeparse.Sarge({})


def test_full_ok(caplog):

    def fn_main():
        pass

    def fn_run():
        pass

    parser = sargeparse.Sarge({
        'description': 'MAIN_DESCRIPTION',
        'epilog': 'MAIN_EPILOG',
        'callback': fn_main,
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

    parser.add_defaults({
        'extra2': 'EXTRA_ARG2',
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
        'callback': fn_run,
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

    assert args.callbacks == [fn_main, fn_run]

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
            'extra2': 'EXTRA_ARG2',
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
                'envvar': 'VARA',
            },
            {
                'names': ['--arg2'],
                'default': '2A',
            },
            {
                'names': ['--arg3'],
                'config_path': 'confA',
            },
        ],
    }, {
        'name': 'subb',
        'arguments': [
            {
                'names': ['--arg1'],
                'envvar': 'VARB',
            },
            {
                'names': ['--arg2'],
                'default': '2B',
            },
            {
                'names': ['--arg3'],
                'config_path': 'confB',
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


def test_callback_dispatch_and_decorator():

    obj_main = {
        'last': True
    }

    obj_sub = {
        'last': False,
        'value': 1
    }

    obj_deco = {
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

    @parser.subcommand({
        'name': 'deco',
        'arguments': [
            {
                'names': ['--arg3'],
                'default': 'A3',
            },
        ]
    })
    def cb_deco(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.values['arg1'] == 'A1'
        assert ctx.values['arg2'] == 'A2'
        assert ctx.values['arg3'] == 'A3'

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
            'arg1': 'A1',
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
            'arg2': 'A2',
        },
        {},
        {},
        {},
        {
            'arg1': 'A1',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test deco')
    args = parser.parse()
    print(args.callbacks)
    assert args.callbacks == [cb_main, cb_deco]
    args.dispatch(obj=obj_deco)
    assert args == ChainMap(
        {
            'arg2': 'A2',
        },
        {},
        {},
        {},
        {
            'arg1': 'A1',
            'arg3': 'A3',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
            'arg3': sargeparse.unset,
        },
    )


def test_show_default_and_help(capsys):

    class CustomObject:
        def __init__(self, value):
            self.value = value

        def __repr__(self):
            return '<CustomObject {}>'.format(self.value)

        def __str__(self):
            return 'custom_object -> {}'.format(self.value)

        def __eq__(self, other):
            if isinstance(other, CustomObject):
                return self.value == other.value

            return super().__eq__(other)

    parser = sargeparse.Sarge({
        'arguments': [
            {
                'names': ['--arg1'],
                'default': 1,
                'type': str,
                'show_default': True,
            },
            {
                'names': ['--arg2'],
                'default': '2',
                'type': int,
                'show_default': True,
            },
            {
                'names': ['--arg3'],
                'default': '3',
                'help': None,
                'show_default': True,
            },
            {
                'names': ['--arg4'],
                'default': 4,
                'help': '',
                'show_default': True,
            },
            {
                'names': ['--arg5'],
                'default': 5,
                'help': sargeparse.suppress,
                'show_default': True,
            },
            {
                'names': ['--arg6'],
                'default': 6,
                'help': None,
                'type': CustomObject,
                'show_default': True,
            },
            {
                'names': ['--arg7'],
                'default': CustomObject(7),
                'type': repr,
                'help': None,
                'show_default': True,
            },
        ],
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test -h')
        parser.parse()

    assert ex.type == SystemExit
    assert ex.value.code == 0

    captured = capsys.readouterr()
    assert re.search(r'^ +--arg1.*(?<=WARNING).*(default: 1)', captured.out, re.MULTILINE)
    assert re.search(r'^ +--arg2.*(?<=WARNING).*(default: 2)', captured.out, re.MULTILINE)
    assert re.search(r'^ +--arg3.*(?<!WARNING).*(default: 3)', captured.out, re.MULTILINE)
    assert re.search(r'^ +--arg4.*(?<!WARNING).*(default: 4)', captured.out, re.MULTILINE)
    assert re.search(r'^ +--arg5', captured.out, re.MULTILINE) is None
    assert re.search(r'^ +--arg6.*(default: 6)', captured.out, re.MULTILINE)
    assert re.search(r'^ +--arg7.*(default: custom_object -> 7)', captured.out, re.MULTILINE)

    sys.argv = shlex.split('test')
    args = parser.parse()

    assert args == ChainMap(
        {},
        {},
        {},
        {},
        {
            'arg1': '1',
            'arg2': 2,
            'arg3': '3',
            'arg4': 4,
            'arg5': 5,
            'arg6': CustomObject(6),
            'arg7': '<CustomObject 7>',

        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
            'arg3': sargeparse.unset,
            'arg4': sargeparse.unset,
            'arg5': sargeparse.unset,
            'arg6': sargeparse.unset,
            'arg7': sargeparse.unset,
        },
    )

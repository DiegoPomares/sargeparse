# pylint: disable=redefined-outer-name
import sys
import shlex
import re
from collections import ChainMap

import pytest

import sargeparse


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


def test_group_descriptions(capsys):
    parser = sargeparse.Sarge({
        'arguments': [
            {
                'names': ['arg1'],
                'group': 'group1',
            },
            {
                'names': ['arg2'],
                'group': 'group2',
            }

        ],
        'group_descriptions': {
            'group1': 'GROUP1 DESC',
        }
    })

    parser.add_arguments({
        'names': ['arg3'],
        'group': 'group3',
    })

    parser.add_group_descriptions({
        'group2': 'GROUP2 DESC',
        'group3': 'GROUP3 DESC',
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test -h')
        parser.parse()

    assert ex.value.code == 0

    captured = capsys.readouterr()
    assert re.search(r'^group1:\s+GROUP1 DESC', captured.out, re.MULTILINE)
    assert re.search(r'^group2:\s+GROUP2 DESC', captured.out, re.MULTILINE)
    assert re.search(r'^group3:\s+GROUP3 DESC', captured.out, re.MULTILINE)


def test_add_usage_to_parent_command_desc(capsys):
    parser = sargeparse.Sarge({
        'subcommands': [
            {
                'name': 'sub1',
                'help': 'SUBC1',
                'add_usage_to_parent_command_desc': True,
                'arguments': [
                    {
                        'names': ['-a1']
                    },
                    {
                        'names': ['b1']
                    },
                ]
            },
            {
                'name': 'sub2',
                'help': 'SUBC2',
                'add_usage_to_parent_command_desc': True,
                'arguments': [
                    {
                        'names': ['-a2']
                    },
                    {
                        'names': ['b2']
                    },
                ]
            },
            {
                'name': 'sub3',
                'help': 'SUBC3',
                'arguments': [
                    {
                        'names': ['-a3']
                    },
                    {
                        'names': ['b3']
                    },
                ]
            },
        ],
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test -h')
        parser.parse()

    assert ex.value.code == 0

    captured = capsys.readouterr()
    assert re.search(r'^\s*test\s+sub1\s*\[\s*-a1\s+A1\s*\].+?b1$', captured.out, re.MULTILINE)
    assert re.search(r'^\s*test\s+sub2\s*\[\s*-a2\s+A2\s*\].+?b2$', captured.out, re.MULTILINE)
    assert not re.search(r'^\s*test\s+sub3\s*\[\s*-a2\s+A3\s*\].+?b3$', captured.out, re.MULTILINE)

    assert re.search(r'^\s*sub1\s+SUBC1', captured.out, re.MULTILINE)
    assert re.search(r'^\s*sub2\s+SUBC2', captured.out, re.MULTILINE)
    assert re.search(r'^\s*sub3\s+SUBC3', captured.out, re.MULTILINE)


def test_help_subcommand(capsys):
    parser = sargeparse.Sarge({
        'subcommands': [
            {
                'name': 'sub1',
                'help': 'SUBC1',
                'add_usage_to_parent_command_desc': True,
                'arguments': [
                    {
                        'names': ['-a1']
                    },
                    {
                        'names': ['b1']
                    },
                ]
            },
            {
                'name': 'sub2',
                'help': 'SUBC2',
                'add_usage_to_parent_command_desc': True,
                'arguments': [
                    {
                        'names': ['-a2']
                    },
                    {
                        'names': ['b2']
                    },
                ]
            },
            {
                'name': 'sub3',
                'help': 'SUBC3',
                'arguments': [
                    {
                        'names': ['-a3']
                    },
                    {
                        'names': ['b3']
                    },
                ]
            },
        ],
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test help')
        parser.parse()

    assert ex.value.code == 0

    captured = capsys.readouterr()
    assert re.search(r'^\s*test\s+sub1\s*\[\s*-a1\s+A1\s*\].+?b1$', captured.out, re.MULTILINE)
    assert re.search(r'^\s*test\s+sub2\s*\[\s*-a2\s+A2\s*\].+?b2$', captured.out, re.MULTILINE)
    assert not re.search(r'^\s*test\s+sub3\s*\[\s*-a2\s+A3\s*\].+?b3$', captured.out, re.MULTILINE)

    assert re.search(r'^\s*sub1\s+SUBC1', captured.out, re.MULTILINE)
    assert re.search(r'^\s*sub2\s+SUBC2', captured.out, re.MULTILINE)
    assert re.search(r'^\s*sub3\s+SUBC3', captured.out, re.MULTILINE)


def test_help_subcommand_when_disabled(capsys):
    parser = sargeparse.Sarge({
        'help_subcommand': False,
        'subcommands': [
            {
                'name': 'sub',
                'help': 'SUBC',
            },

        ],
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test help')
        parser.parse()

    assert ex.value.code == 2

    captured = capsys.readouterr()
    assert "invalid choice: 'help'" in captured.err


def test_print_help_and_exit_if_last(capsys):
    parser = sargeparse.Sarge({
        'print_help_and_exit_if_last': True,
        'subcommands': [
            {
                'name': 'sub2',
                'print_help_and_exit_if_last': False,
                'subcommands': [
                    {
                        'name': 'sub3',
                        'print_help_and_exit_if_last': True,
                    }
                ]
            }
        ]
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test sub2 sub3')
        args = parser.parse()
        args.dispatch()

    assert ex.value.code == 0

    captured = capsys.readouterr()
    assert re.search(r'\s*usage:\s+test sub2 sub3.*$', captured.err, re.MULTILINE)

    # Shouldn't exit even though no callback was added
    sys.argv = shlex.split('test sub2')
    args = parser.parse()
    args.dispatch()

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test')
        args = parser.parse()
        args.dispatch()

    assert ex.value.code == 0

    captured = capsys.readouterr()
    assert re.search(r'\s*usage:\s+test.*$', captured.err, re.MULTILINE)


def test_print_help_and_exit_if_last_with_existing_callback(capsys):
    ctx_obj = {
        'value': 0,
    }

    def add_one(ctx):
        ctx.obj['value'] += 1

    parser = sargeparse.Sarge({
        'print_help_and_exit_if_last': True,
        'callback': add_one,
        'subcommands': [
            {
                'name': 'sub2',
                'print_help_and_exit_if_last': True,
            }
        ]
    })

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test sub2')
        args = parser.parse()
        args.dispatch(obj=ctx_obj)

    assert ex.value.code == 0
    assert ctx_obj['value'] == 1

    captured = capsys.readouterr()
    assert re.search(r'\s*usage:\s+test sub2.*$', captured.err, re.MULTILINE)

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test')
        args = parser.parse()
        args.dispatch()

    assert ex.value.code == 0
    assert ctx_obj['value'] == 1

    captured = capsys.readouterr()
    assert re.search(r'\s*usage:\s+test.*$', captured.err, re.MULTILINE)

    with pytest.raises(SystemExit) as ex:
        sys.argv = shlex.split('test sub2')
        args = parser.parse()
        args.dispatch(obj=ctx_obj)

    assert ex.value.code == 0
    assert ctx_obj['value'] == 2

    captured = capsys.readouterr()
    assert re.search(r'\s*usage:\s+test sub2.*$', captured.err, re.MULTILINE)

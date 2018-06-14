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
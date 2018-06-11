# pylint: disable=redefined-outer-name
import sys
import shlex
import re

import pytest

import sargeparse


def test_mutex_group_required(capsys):
    definition = {
        'arguments': [
            {
                'names': ['-x'],
                'mutex_group': 1,
            },
            {
                'names': ['-y'],
                'mutex_group': 1,
            },
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test -h')

    with pytest.raises(SystemExit) as ex:
        parser.parse()
    captured = capsys.readouterr()
    assert re.search(r'\[\s*?-x\s+?.+?\|\s*?-y\s+?.+?\]', captured.out)

    definition['arguments'][0]['required'] = True
    parser = sargeparse.Sarge(definition)
    with pytest.raises(ValueError) as ex:
        parser.parse()

    assert 'must have the same value' in str(ex)

    definition['arguments'][1]['required'] = True
    parser = sargeparse.Sarge(definition)
    with pytest.raises(SystemExit) as ex:
        parser.parse()
    captured = capsys.readouterr()
    assert re.search(r'\(\s*?-x\s+?.+?\|\s*?-y\s+?.+?\)', captured.out)

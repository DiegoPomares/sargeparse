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


def test_mutex_group_global(capsys):
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

    definition['arguments'][0]['global'] = True
    parser = sargeparse.Sarge(definition)
    with pytest.raises(ValueError) as ex:
        parser.parse()

    assert 'must have the same value' in str(ex)

    definition['arguments'][1]['global'] = True
    parser = sargeparse.Sarge(definition)
    with pytest.raises(SystemExit) as ex:
        parser.parse()
    captured = capsys.readouterr()
    assert re.search(r'\[\s*?-x\s+?.+?\|\s*?-y\s+?.+?\]', captured.out)


def test_mutex_group_global_required(capsys):
    definition = {
        'arguments': [
            {
                'names': ['-x'],
                'mutex_group': 1,
                'required': True,
                'global': True,
            },
            {
                'names': ['-y'],
                'mutex_group': 1,
                'required': False,
                'global': True,
            },
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test -h')

    parser = sargeparse.Sarge(definition)
    with pytest.raises(ValueError) as ex:
        parser.parse()

    assert 'must have the same value' in str(ex)


def test_mutex_group_groups(capsys):
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

    definition['arguments'][0]['group'] = 'G'
    parser = sargeparse.Sarge(definition)
    with pytest.raises(ValueError) as ex:
        parser.parse()

    assert 'must have the same value' in str(ex)

    definition['arguments'][1]['group'] = 'G'
    parser = sargeparse.Sarge(definition)
    with pytest.raises(SystemExit) as ex:
        parser.parse()
    captured = capsys.readouterr()
    assert re.search(r'\[\s*?-x\s+?.+?\|\s*?-y\s+?.+?\]', captured.out)


def test_mutex_group_groups_required(capsys):
    definition = {
        'arguments': [
            {
                'names': ['-x'],
                'mutex_group': 1,
                'required': True,
                'group': 'A',
            },
            {
                'names': ['-y'],
                'mutex_group': 1,
                'required': False,
                'group': 'B',
            },
        ],
    }

    parser = sargeparse.Sarge(definition)
    sys.argv = shlex.split('test -h')

    parser = sargeparse.Sarge(definition)
    with pytest.raises(ValueError) as ex:
        parser.parse()

    assert 'must have the same value' in str(ex)

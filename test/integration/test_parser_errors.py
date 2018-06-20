# pylint: disable=redefined-outer-name
import re

from unittest.mock import patch

import pytest

import sargeparse


def test_allow_abbrev():
    definition = {
        'allow_abbrev': True,
    }

    # Pretend python version is < 3.5
    with patch('sargeparse._parser.parser.python_version', return_value=True):
        with pytest.raises(ValueError) as ex:
            sargeparse.Sarge(definition)

    assert 'not supported' in str(ex)


def test_help_in_main_command():
    definition = {
        'help': 'HELP MESSAGE',
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert 'applies only to subcommands' in str(ex)


def test_no_name_in_subcommand():
    definition = {
        'subcommands': [
            {
                'help': 'SUBCOMMAND',
            }
        ],
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert 'missing or invalid' in str(ex)


def test_callback_not_callable():
    definition = {
        'callback': 'test'
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert 'not callable' in str(ex)


def test_add_usage_to_parent_command_desc_in_main_command():
    definition = {
        'add_usage_to_parent_command_desc': True,
    }

    with pytest.raises(TypeError) as ex:
        sargeparse.Sarge(definition)

    assert 'applies only to subcommands' in str(ex)


def test_warning_subcommands_positional_arguments(caplog):
    definition = {
        'arguments': [
            {
                'names': ['arg'],
            }
        ],
        'subcommands': [
            {
                'name': 'sub',
            }
        ],
    }

    sargeparse.Sarge(definition)

    assert 'probably a bad idea' in caplog.text


def test_warning_properties_different_from_none(caplog):
    definition = {
        'prog': 'main_prog',
        'usage': 'main_usage',
        'arguments': [
            {
                'names': ['arg'],
            }
        ],
        'subcommands': [
            {
                'name': 'sub',
                'prog': 'sub_prog',
                'usage': 'sub_usage',
            }
        ],
        'subparser': {
            'prog': 'subparser_prog',
            'help': 'subparser_help',
        }
    }

    sargeparse.Sarge(definition)

    assert re.search(r'prog.*better than.*main_prog', caplog.text)
    assert re.search(r'usage.*better than.*main_usage', caplog.text)

    assert re.search(r'prog.*better than.*sub_prog', caplog.text)
    assert re.search(r'usage.*better than.*sub_usage', caplog.text)

    assert re.search(r'prog.*better than.*subparser_prog', caplog.text)
    assert re.search(r'help.*better than.*subparser_help', caplog.text)

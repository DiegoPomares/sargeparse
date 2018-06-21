# pylint: disable=redefined-outer-name

import re

from unittest.mock import patch

import pytest

from sargeparse.custom import ArgumentParser, HelpFormatter


def test_ap_error(capsys):
    help_msg = 'HELP_MESSAGE'
    error_msg = 'ERROR_MESSAGE'

    ap = ArgumentParser()

    with pytest.raises(SystemExit) as ex, \
            patch('sargeparse.custom.ArgumentParser.print_usage', side_effect=(lambda: print(help_msg))):
        ap.error(error_msg)

    assert ex.value.code == 2

    captured = capsys.readouterr()

    assert captured.out.startswith(help_msg)
    assert captured.err.startswith('error: {}'.format(error_msg))


def test_subcommand_indentation(capsys):
    # With subparsers header
    ap = ArgumentParser(formatter_class=HelpFormatter)
    subparsers = ap.add_subparsers(title='SUBP_TITLE', metavar='SUBP_META', help='SUBP_HELP')
    subparsers.add_parser('sub', help='SUBC_HELP')

    with pytest.raises(SystemExit) as ex:
        ap.parse_args(args=['--help'])

    assert ex.value.code == 0

    captured = capsys.readouterr()

    match = re.search(r'^(?P<indent>\s+)SUBP_META\s+SUBP_HELP\s*$', captured.out, re.MULTILINE)
    assert match
    indent = match.group('indent')

    match = re.search(r'^(?P<indent>\s+)sub\s+SUBC_HELP\s*$', captured.out, re.MULTILINE)
    assert match
    assert match.group('indent') == '{0}{0}'.format(indent)

    # Remove subparsers header
    ap = ArgumentParser(formatter_class=HelpFormatter)
    subparsers = ap.add_subparsers(title='SUBP_TITLE', metavar='SUBP_META')
    subparsers.add_parser('sub', help='SUBC_HELP')

    with pytest.raises(SystemExit) as ex:
        ap.parse_args(args=['--help'])

    assert ex.value.code == 0

    captured = capsys.readouterr()

    match = re.search(r'^(?P<indent>\s+)sub\s+SUBC_HELP\s*$', captured.out, re.MULTILINE)
    assert match
    assert match.group('indent') == indent

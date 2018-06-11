# pylint: disable=redefined-outer-name

from unittest.mock import patch

import pytest

from sargeparse.custom import ArgumentParser


@pytest.fixture
def ap():
    return ArgumentParser()


def test_ap_error(ap, capsys):
    help_msg = 'HELP_MESSAGE'
    error_msg = 'ERROR_MESSAGE'

    with pytest.raises(SystemExit) as ex, \
            patch('sargeparse.custom.ArgumentParser.print_usage', side_effect=(lambda: print(help_msg))):
        ap.error(error_msg)

    assert ex.value.code == 2

    captured = capsys.readouterr()

    assert captured.out.startswith(help_msg)
    assert captured.err.startswith('error: {}'.format(error_msg))

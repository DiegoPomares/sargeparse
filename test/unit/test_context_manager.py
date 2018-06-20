# pylint: disable=redefined-outer-name
import pytest

from sargeparse.context_manager import check_kwargs


def test_check_kwargs_not_found():
    d = {
        1: 1,
        2: 2,
    }

    with pytest.raises(KeyError) as ex:
        with check_kwargs(d):
            d.pop(1)
            d.pop(2)
            d.pop(3)

    assert 'not in kwargs' in str(ex)


def test_check_kwargs_unprocessed():
    d = {
        1: 1,
        2: 2,
    }

    with pytest.raises(RuntimeError) as ex:
        with check_kwargs(d):
            d.pop(1)

    assert 'Unrecognized' in str(ex)

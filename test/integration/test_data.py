import pytest

from sargeparse._parser.data import ArgumentData


def test_argument_data_precedence():
    ad = ArgumentData(None)
    assert ad.maps == [
        ad._data_sources['override'],
        ad._data_sources['cli'],
        ad._data_sources['environment'],
        ad._data_sources['configuration'],
        ad._data_sources['defaults'],
        ad._data_sources['arg_default'],
    ]

    ad.set_precedence(['configuration', 'environment', 'cli', 'defaults'])
    assert ad.maps == [
        ad._data_sources['override'],
        ad._data_sources['configuration'],
        ad._data_sources['environment'],
        ad._data_sources['cli'],
        ad._data_sources['defaults'],
        ad._data_sources['arg_default'],
    ]

    ad = ArgumentData(None, precedence=['cli', 'environment', 'defaults', 'configuration'])
    assert ad.maps == [
        ad._data_sources['override'],
        ad._data_sources['cli'],
        ad._data_sources['environment'],
        ad._data_sources['defaults'],
        ad._data_sources['configuration'],
        ad._data_sources['arg_default'],
    ]

    with pytest.raises(TypeError) as ex:
        ad.set_precedence()  # pylint: disable=no-value-for-parameter

    assert 'missing 1' in str(ex)

    with pytest.raises(TypeError) as ex:
        ad.set_precedence(['cli', 'default'])

    assert 'must contain all' in str(ex)

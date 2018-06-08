from sargeparse.consts import _sentinel_factory


def test_sentinel_factory():
    test = _sentinel_factory('TEST')
    assert test.__repr__() == '<sargeparse.TEST>'
    assert test + 10 == 10
    assert 100 + test == 100

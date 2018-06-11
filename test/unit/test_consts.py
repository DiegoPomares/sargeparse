from itertools import permutations

import sargeparse.consts


def test_sentinel_factory():
    test = sargeparse.consts._sentinel_factory('TEST')
    assert test.__repr__() == '<sargeparse.TEST>'
    assert test + 10 == 10
    assert 100 + test == 100

    for value in (0, 0.0, False, 1, 1.0, True):
        assert test != value
        assert value != test


def test_equality():
    sentinels = (sargeparse.consts.unset, sargeparse.consts.die, sargeparse.consts.stop)

    for sentinel in sentinels:
        assert sentinel == sentinel(10)

    for sentinel1, sentinel2 in permutations((sentinels), 2):
        assert sentinel1 != sentinel2

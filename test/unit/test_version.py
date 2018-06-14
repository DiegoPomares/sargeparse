# pylint: disable=redefined-outer-name
import random

import pytest
from sys import version_info

from sargeparse.version import python_version


def test_python_versions():
    current = '{}.{}.{}'.format(version_info.major, version_info.minor, version_info.micro)

    low = [str(version_info.major - 1)]
    low.append('{}.{}'.format(low[0], version_info.minor))
    low.append('{}.{}'.format(low[1], version_info.micro))
    low *= 24
    random.shuffle(low)

    high = [str(version_info.major + 1)]
    high.append('{}.{}'.format(high[0], version_info.minor))
    high.append('{}.{}'.format(high[1], version_info.micro))
    high *= 24
    random.shuffle(high)

    for low, high in zip(low, high):
        assert python_version('>{}'.format(low))
        assert python_version('>={}'.format(low))
        assert python_version('<{}'.format(high))
        assert python_version('<={}'.format(high))
        assert python_version('!={}'.format(low))
        assert python_version('!={}'.format(high))

        assert python_version('!={}'.format(current)) is False
        assert python_version('<{}'.format(low)) is False
        assert python_version('<={}'.format(low)) is False
        assert python_version('>{}'.format(high)) is False
        assert python_version('>={}'.format(high)) is False
        assert python_version('=={}'.format(low)) is False
        assert python_version('=={}'.format(high)) is False
        assert python_version('<{}'.format(low), '>{}'.format(high)) is False

    assert python_version('=={}'.format(current))
    assert python_version('>{}'.format(low), '<{}'.format(high))

    cases = [
        current,  # Lacks ==
        '<=10.1.1',  # Major version too big
        '<4.200.1',  # Minor version too big
        '>=1.1.1000',  # Micro version too big
        '>110100',  # No dots
        'ksjdif',
        '',
    ]
    for case in cases:
        print(case)
        with pytest.raises(TypeError) as ex:
            python_version(case)

        assert 'Invalid version specification' in str(ex)

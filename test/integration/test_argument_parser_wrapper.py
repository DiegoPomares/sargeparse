import pytest

from sargeparse.sarge import _ArgumentParserWrapper
from sargeparse._parser.argument import Argument
from sargeparse._parser.group import MutualExclussionGroup


def test_argparse_add_obj_other_than_group():
    apw = _ArgumentParserWrapper(None)

    argument = Argument(
        {
            'names': ['-a', '--arg'],
        },
        show_warnings=True,
        prefix_chars='-',
        main_command=True,
    )

    mutex = MutualExclussionGroup(required=True)

    objs = [None, 1, True, argument, mutex]

    for obj in objs:
        with pytest.raises(RuntimeError) as ex:
            apw.add_arguments(obj)

        assert 'argparse arguments must always be groups' in str(ex)

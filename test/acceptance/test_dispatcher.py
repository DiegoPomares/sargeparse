# pylint: disable=redefined-outer-name
import sys
import shlex
import re

from types import LambdaType
from collections import ChainMap

import pytest
import sargeparse


def test_callback_dispatch_with_decorators():

    obj_main = {
        'last': True
    }

    obj_sub = {
        'last': False,
        'value': 1
    }

    obj_deco = {
        'last': False,
        'value': 1
    }

    obj_sb_dec = {
        'last': False,
        'value': 1
    }

    def cb_sub(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.data['arg1'] == 'A1'
        assert ctx.data['arg2'] == 'A2'

        assert ctx.return_value == 10
        assert ctx.parser.prog == 'test sub'
        assert re.match(r'\s*usage:\s+test sub.*$', ctx.parser.usage)
        assert all(s not in ctx.parser.help for s in ('deco', 'sb_dec'))

    @sargeparse.Sarge.decorator({
        'arguments': [
            {
                'names': ['--arg1'],
                'default': 'A1',
            },
            {
                'names': ['--arg2'],
            },
        ],
        'subcommands': [
            {
                'name': 'sub',
                'callback': cb_sub,
            }
        ]
    })
    def parser(ctx):
        assert ctx.last == ctx.obj['last']
        assert ctx.return_value is None
        assert ctx.parser.prog == 'test'
        assert re.match(r'\s*usage:\s+test.*$', ctx.parser.usage)
        assert all(s in ctx.parser.help for s in ('sub', 'deco', 'sb_dec'))

        if ctx.last:
            assert ctx.data['arg1'] == 'A1'
            assert ctx.data['arg2'] == sargeparse.unset

        else:
            assert ctx.obj['value'] == 1

            # Change ctx_obj and parsed values for next callback
            ctx.obj['value'] = 2
            ctx.data['arg2'] = 'A2'

            # Changing this should have no effect
            ctx.last = -1

        return 10

    @parser.subcommand_decorator({
        'name': 'deco',
        'arguments': [
            {
                'names': ['--arg3'],
                'default': 'A3',
            },
        ]
    })
    def cb_deco(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.data['arg1'] == 'A1'
        assert ctx.data['arg2'] == 'A2'
        assert ctx.data['arg3'] == 'A3'

        assert ctx.return_value == 10
        assert ctx.parser.prog == 'test deco'
        assert re.match(r'\s*usage:\s+test deco.*$', ctx.parser.usage)
        assert all(s not in ctx.parser.help for s in ('sub', 'sb_dec'))

    @sargeparse.SubCommand.decorator({
        'name': 'sb_dec',
        'arguments': [
            {
                'names': ['--arg4'],
                'default': 'A4',
            },
        ]
    })
    def sb_dec(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.data['arg1'] == 'A1'
        assert ctx.data['arg2'] == 'A2'
        assert ctx.data['arg4'] == 'A4'

        assert ctx.return_value == 10
        assert ctx.parser.prog == 'test sb_dec'
        assert re.match(r'\s*usage:\s+test sb_dec.*$', ctx.parser.usage)
        assert all(s not in ctx.parser.help for s in ('sub', 'deco'))

    parser.add_subcommands(sb_dec)

    sys.argv = shlex.split('test')
    args = parser.parse()
    assert args.callbacks == [parser.__call__.fn]
    args.dispatch(obj=obj_main)
    assert args == ChainMap(
        {},
        {},
        {},
        {},
        {
            'arg1': 'A1',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test sub')
    args = parser.parse()
    assert args.callbacks == [parser.__call__.fn, cb_sub]
    args.dispatch(obj=obj_sub)
    assert args == ChainMap(
        {
            'arg2': 'A2',
        },
        {},
        {},
        {},
        {
            'arg1': 'A1',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test deco')
    args = parser.parse()
    assert args.callbacks == [parser.__call__.fn, cb_deco]
    args.dispatch(obj=obj_deco)
    assert args == ChainMap(
        {
            'arg2': 'A2',
        },
        {},
        {},
        {},
        {
            'arg1': 'A1',
            'arg3': 'A3',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
            'arg3': sargeparse.unset,
        },
    )

    sys.argv = shlex.split('test sb_dec')
    args = parser.parse()
    assert args.callbacks == [parser.__call__.fn, sb_dec.__call__.fn]
    args.dispatch(obj=obj_sb_dec)
    assert args == ChainMap(
        {
            'arg2': 'A2',
        },
        {},
        {},
        {},
        {
            'arg1': 'A1',
            'arg4': 'A4',
        },
        {
            'arg1': sargeparse.unset,
            'arg2': sargeparse.unset,
            'arg4': sargeparse.unset,
        },
    )


def test_callback_dispatch_special_returns():
    def cb_main(ctx):
        if ctx.obj['value'] == 1:
            ctx.obj['value'] = 10
            return sargeparse.die(100)

        return None

    def cb_sub2(ctx):
        if ctx.obj['value'] == 2:
            ctx.obj['value'] = 20
            return sargeparse.stop(200)

        return None

    def cb_sub3(ctx):
        assert ctx.last is True
        ctx.obj['value'] = 30
        return 300

    parser = sargeparse.Sarge({
        'callback': cb_main,
        'subcommands': [
            {
                'name': 'sub2',
                'callback': cb_sub2,
                'subcommands': [
                    {
                        'name': 'sub3',
                        'callback': cb_sub3
                    }
                ]
            }
        ]
    })

    sys.argv = shlex.split('test sub2 sub3')
    args = parser.parse()
    assert args.callbacks == [cb_main, cb_sub2, cb_sub3]

    obj = {'value': 1}
    with pytest.raises(SystemExit) as ex:
        args.dispatch(obj=obj)
    assert ex.value.code == 100
    assert obj['value'] == 10

    obj = {'value': 2}
    assert args.dispatch(obj=obj) == 200
    assert obj['value'] == 20

    obj = {'value': 3}
    assert args.dispatch(obj=obj) == 300
    assert obj['value'] == 30


def test_callback_dispatch_skipping():
    obj = {'const': 0}

    def cb_main(ctx):
        ctx.obj['value'] = 10
        return 100

    def cb_sub3(ctx):
        assert ctx.last is True
        assert ctx.obj['const'] == 0
        assert ctx.obj['value'] == 10
        assert ctx.return_value == 100

        ctx.obj['value'] = 30
        return 300

    parser = sargeparse.Sarge({
        'callback': cb_main,
        'subcommands': [
            {
                'name': 'sub2',
                'subcommands': [
                    {
                        'name': 'sub3',
                        'callback': cb_sub3
                    }
                ]
            }
        ]
    })

    sys.argv = shlex.split('test sub2 sub3')
    args = parser.parse()

    assert len(args.callbacks) == 3
    assert args.callbacks[0] == cb_main
    assert isinstance(args.callbacks[1], LambdaType)
    assert args.callbacks[2] == cb_sub3

    assert args.dispatch(obj=obj) == 300
    assert obj['value'] == 30

    sys.argv = shlex.split('test sub2')
    args = parser.parse()

    assert len(args.callbacks) == 2
    assert args.callbacks[0] == cb_main
    assert isinstance(args.callbacks[1], LambdaType)

    assert args.dispatch(obj=obj) == 100
    assert obj['value'] == 10

    sys.argv = shlex.split('test')
    args = parser.parse()

    assert args.callbacks == [cb_main]
    assert args.dispatch(obj=obj) == 100
    assert obj['value'] == 10


def test_callback_decorator_duplicate_sarge():
    def cb_main(ctx):
        pass

    with pytest.raises(ValueError) as ex:
        @sargeparse.Sarge.decorator({
            'callback': cb_main,
        })
        def cb_main_2_(ctx):
            pass

    assert "Cannot use the decorator with a 'callback' in the definition" in str(ex)


def test_callback_decorator_duplicate_subcommand():
    def cb_main(ctx):
        pass

    with pytest.raises(ValueError) as ex:
        @sargeparse.SubCommand.decorator({
            'callback': cb_main,
        })
        def cb_main_2_(ctx):
            pass

    assert "Cannot use the decorator with a 'callback' in the definition" in str(ex)


def test_callback_subcommand_decorator_duplicate():
    def cb_sub(ctx):
        pass

    parser = sargeparse.Sarge({})

    with pytest.raises(ValueError) as ex:
        @parser.subcommand_decorator({
            'callback': cb_sub,
        })
        def cb_sub2_(ctx):
            pass

    assert "Cannot use the subcommand decorator with a 'callback' in the definition" in str(ex)


def test_callback_with_print_help_and_exit_if_last():
    def cb_sub(ctx):
        pass

    with pytest.raises(ValueError) as ex:
        sargeparse.Sarge({
            'callback': cb_sub,
            'print_help_and_exit_if_last': True,
        })

    assert re.search(r'callback.*print_help_and_exit_if_last.*mutually exclusive', str(ex))

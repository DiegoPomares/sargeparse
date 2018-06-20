# pylint: disable=redefined-outer-name
import sys
import shlex

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

    obj_sub_deco = {
        'last': False,
        'value': 1
    }

    def cb_sub(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.data['arg1'] == 'A1'
        assert ctx.data['arg2'] == 'A2'

        assert ctx.return_value == 10

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

    @sargeparse.SubCommand.decorator({
        'name': 'sub_deco',
        'arguments': [
            {
                'names': ['--arg4'],
                'default': 'A4',
            },
        ]
    })
    def sub_deco(ctx):
        assert ctx.last is True
        assert ctx.obj['value'] == 2
        assert ctx.data['arg1'] == 'A1'
        assert ctx.data['arg2'] == 'A2'
        assert ctx.data['arg4'] == 'A4'

    parser.add_subcommands(sub_deco)

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

    sys.argv = shlex.split('test sub_deco')
    args = parser.parse()
    assert args.callbacks == [parser.__call__.fn, sub_deco.__call__.fn]
    args.dispatch(obj=obj_sub_deco)
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


def test_callback_decorator_duplicate_sarge():
    def cb_main(ctx):
        pass

    with pytest.raises(ValueError) as ex:
        @sargeparse.Sarge.decorator({
            'callback': cb_main,
        })
        def cb_main_2(ctx):
            pass

    assert "Cannot use the decorator with a 'callback' in the definition" in str(ex)


def test_callback_decorator_duplicate_subcommand():
    def cb_main(ctx):
        pass

    with pytest.raises(ValueError) as ex:
        @sargeparse.SubCommand.decorator({
            'callback': cb_main,
        })
        def cb_main_2(ctx):
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
        def cb_sub2(ctx):
            pass

    assert "Cannot use the subcommand decorator with a 'callback' in the definition" in str(ex)

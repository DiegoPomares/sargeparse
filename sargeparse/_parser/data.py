import sys
from collections import ChainMap

import sargeparse.consts

from sargeparse._parser.parser import Parser


class ArgumentData(ChainMap):
    _default_precedence = ['cli', 'environment', 'configuration', 'defaults']

    def __init__(self, parser: Parser, precedence=None):
        super().__init__()

        self._parser = parser
        self._config_data = {}
        self._data_sources = {}
        self.callbacks = []

        for source in self._format_precedence_list(self._default_precedence):
            self._data_sources[source] = {}

        self._override = self._data_sources['override']
        self.cli = self._data_sources['cli']
        self.environment = self._data_sources['environment']
        self.configuration = self._data_sources['configuration']
        self.defaults = self._data_sources['defaults']
        self._arg_default = self._data_sources['arg_default']

        self.parser_data = {}

        self.set_precedence(precedence)

    def set_precedence(self, precedence):
        precedence = precedence or self._default_precedence

        difference = set(self._default_precedence).symmetric_difference(set(precedence))
        if difference:
            msg = "Precedence must contain all and only these elements: {}"
            raise TypeError(msg.format(self._default_precedence))

        precedence = self._format_precedence_list(precedence)
        self.maps = [self._data_sources[k] for k in precedence]

    def clear_all(self):
        for d in self._data_sources.values():
            d.clear()

    def dispatch(self, *, obj=None):
        last_callback = len(self.callbacks) - 1
        return_value = None

        for i, fn in enumerate(self.callbacks):
            parser_data = self.parser_data[fn.parser.parser_key()]
            last = (i == last_callback)
            ctx = Context(
                data=self,
                obj=obj,
                parser_data=parser_data,
                last=last,
                return_value=return_value,

            )
            return_value = fn(ctx)

            if return_value == sargeparse.die:
                sys.exit(return_value.value)

            elif return_value == sargeparse.stop:
                return_value = return_value.value
                break

        return return_value

    @staticmethod
    def _format_precedence_list(precedence):
        return ['override'] + precedence + ['arg_default']

    def _remove_unset_from_data_sources_cli(self):
        for k, v in list(self.cli.items()):
            if v == sargeparse.unset:
                self.cli.pop(k)

    def _move_defaults_from_data_sources_cli(self, parser=None):
        parser = parser or self._parser

        key = parser.parser_key()
        if key not in self.cli:
            return

        defaults = self.cli[key].get('defaults', {})

        self.defaults.update(defaults)

        for subparser in parser.subparsers:
            self._move_defaults_from_data_sources_cli(subparser)

    def _parse_callbacks(self):
        self.callbacks = self._get_callbacks()

    def _get_callbacks(self, parser=None):
        parser = parser or self._parser
        callback_list = []

        key = parser.parser_key()
        if key not in self.cli:
            return []

        callback = self.cli[key].get('callback')

        if callback:
            callback_list.append(callback)

        for subparser in parser.subparsers:
            callback_list.extend(
                self._get_callbacks(subparser)
            )

        return callback_list

    def _parse_envvars_and_defaults(self, parser=None):
        parser = parser or self._parser

        # No point in adding data from subcommands that did not run
        key = parser.parser_key()
        if key not in self.cli:
            return

        for argument in parser.arguments:
            dest = argument.dest

            envvar = argument.get_value_from_envvar(default=sargeparse.unset)
            if envvar != sargeparse.unset:
                self.environment[dest] = envvar

            default = argument.get_default_value(default=sargeparse.unset, apply_type=True)
            if default != sargeparse.unset:
                self.defaults[dest] = default

            self._arg_default[dest] = parser.argument_parser_kwargs['argument_default']

        for subparser in parser.subparsers:
            self._parse_envvars_and_defaults(subparser)

    def _parse_config(self, config, parser=None):
        parser = parser or self._parser
        self._config_data = config

        # No point in adding data from subcommands that did not run
        key = parser.parser_key()
        if key not in self.cli:
            return

        for argument in parser.arguments:
            dest = argument.dest

            config_value = argument.get_value_from_config(config, default=sargeparse.unset)
            if config_value != sargeparse.unset:
                self.configuration[dest] = config_value

            self._arg_default[dest] = parser.argument_parser_kwargs['argument_default']

        for subparser in parser.subparsers:
            self._parse_config(config, subparser)

    def _remove_parser_key_from_data_sources_cli(self, parser=None):
        parser = parser or self._parser

        key = parser.parser_key()
        if key not in self.cli:
            return

        self.cli.pop(key)

        for subparser in parser.subparsers:
            self._remove_parser_key_from_data_sources_cli(subparser)


class Context:
    def __init__(self, **kwargs):
        self.data = kwargs.get('data')
        self.obj = kwargs.get('obj')
        self.parser = ParserData(**kwargs.get('parser_data'))
        self.last = kwargs.get('last')
        self.return_value = kwargs.get('return_value')


class ParserData:
    def __init__(self, **parser_data):
        self.prog = parser_data['prog']
        self.help = parser_data['help']
        self.usage = parser_data['usage']

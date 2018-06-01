from collections import ChainMap

import sargeparse.consts


class DataMerger(ChainMap):
    _default_precedence = ['cli', 'environment', 'configuration', 'defaults']

    def __init__(self, parser, precedence=None):
        super().__init__()

        self._parser = parser
        self._data_sources = {}

        for source in self._format_precedence_list(self._default_precedence):
            self._data_sources[source] = {}

        self._override = self._data_sources['override']
        self.cli = self._data_sources['cli']
        self.environment = self._data_sources['environment']
        self.configuration = self._data_sources['configuration']
        self.defaults = self._data_sources['defaults']
        self._arg_default = self._data_sources['arg_default']

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

    @staticmethod
    def _format_precedence_list(precedence):
        return ['override'] + precedence + ['arg_default']

    def _remove_unset_from_collected_data_cli(self):
        for k, v in list(self.cli.items()):
            if v == sargeparse.unset:
                self.cli.pop(k)

    def _move_defaults_from_collected_data_cli(self, parser=None):
        parser = parser or self._parser

        key = parser.default_mask()
        defaults = self.cli.pop(key, {})

        self.defaults.update(defaults)

        for subparser in parser.subparsers:
            self._move_defaults_from_collected_data_cli(subparser)

    def _get_callbacks(self, parser=None):
        parser = parser or self._parser

        callback_list = []

        key = parser.callback_mask()
        callback = self.cli.pop(key, None)

        if callback:
            callback_list.append(callback)

        for subparser in parser.subparsers:
            callback_list.extend(
                self._get_callbacks(subparser)
            )

        return callback_list

    def _parse_envvars_and_defaults(self, parser=None):
        parser = parser or self._parser

        for argument in parser.arguments:
            dest = argument.dest

            envvar = argument.get_value_from_envvar(default=sargeparse.unset)
            if envvar != sargeparse.unset:
                self.environment[dest] = envvar

            default = argument.get_default_value(default=sargeparse.unset)
            if default != sargeparse.unset:
                self.defaults[dest] = default

            self._arg_default[dest] = parser.argument_parser_kwargs['argument_default']

        for subparser in parser.subparsers:
            self._parse_envvars_and_defaults(subparser)

    def _parse_config(self, config, parser=None):
        parser = parser or self._parser

        for argument in parser.arguments:
            dest = argument.dest

            config_value = argument.get_value_from_config(config, default=sargeparse.unset)
            if config_value != sargeparse.unset:
                self.configuration[dest] = config_value

            self._arg_default[dest] = parser.argument_parser_kwargs['argument_default']

        for subparser in parser.subparsers:
            self._parse_config(config, subparser)

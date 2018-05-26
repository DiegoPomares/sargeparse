import sys
import logging
import collections

import sargeparse.consts

from sargeparse.custom import ArgumentParser, HelpFormatter
from sargeparse.parser._argument import Argument

LOG = logging.getLogger(__name__)


class Parser:
    _default_precedence = ['cli', 'environment', 'configuration', 'defaults']
    _custom_ap_params = ['help_subcommand']

    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        self._subcommand = kwargs.pop('_subcommand', False)
        self._show_warnings = kwargs.pop('show_warnings', True)
        self._prefix_chars = definition.get('prefix_chars', '-')

        self._argument_data = None
        self._parsed_data = None
        self._has_positional_arguments = False

        self.arguments = []
        self.subcommand_definitions = []
        self.subparsers_kwargs = {}
        self.add_arguments(*definition.pop('arguments', []))
        self.add_subcommands(*definition.pop('subcommands', []))
        self.config_subparsers(**definition.pop('subparsers', {}))

        self.group_descriptions = definition.pop('group_descriptions', {})
        self.default_kwargs = definition.pop('defaults', {})
        self.argument_parser_kwargs = definition

        if not self._subcommand:
            self.help_subcommand = definition.pop('help_subcommand', True)
            self._preprocess_ap_kwargs(self.argument_parser_kwargs, subcommand=False)

            precedence = ['override'] + self._default_precedence + ['arg_default']
            self._argument_data = {k: {} for k in precedence}
            self._parsed_data = collections.ChainMap()
            self.set_precedence()

    # ------ User methods ------
    def add_arguments(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            self.arguments.append(Argument(
                definition,
                subcommand=self._subcommand,
                show_warnings=self._show_warnings,
                prefix_chars=self._prefix_chars,
            ))

    def add_subcommands(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            self._preprocess_ap_kwargs(definition, subcommand=True)

            self.subcommand_definitions.append(definition)

    def config_subparsers(self, **kwargs):
        self._log_warning_if_elements_are_different_from_none(kwargs, 'prog', 'help')

        kwargs.setdefault('title', 'subcommands')
        kwargs.setdefault('metavar', 'SUBCOMMAND')
        kwargs.setdefault('help', None)

        self.subparsers_kwargs = kwargs

    def add_defaults(self, **kwargs):
        self.default_kwargs.update(kwargs)

    def add_group_descriptions(self, **kwargs):
        self.group_descriptions.update(kwargs)

    def parse(self, argv=None, read_config=None):
        argv = argv or sys.argv[1:]

        self._parse_cli_arguments(argv)
        self._set_arg_default_dict_from_cli_dict()
        self._parse_envvars_and_defaults()

        # Callback
        if read_config:
            config = read_config(self._parsed_data)
            self._parse_config(config)
        else:
            self._argument_data['configuration'].clear()

        return self._parsed_data

    def set_precedence(self, precedence=None):
        precedence = precedence or self._default_precedence

        difference = set(self._default_precedence).symmetric_difference(set(precedence))
        if difference:
            msg = "Precedence must contain all and only these elements: {}"
            raise TypeError(msg.format(self._default_precedence))

        precedence = ['override'] + precedence + ['arg_default']
        self._parsed_data.maps = [self._argument_data[k] for k in precedence]

    # ------ ArgumentParser kwargs pre-processors ------
    def _preprocess_ap_kwargs(self, definition, *, subcommand):
        self._preprocess_base_ap_kwargs(definition)

        if subcommand:
            self._preprocess_subcommand_ap_kwargs(definition)
        else:
            self._preprocess_parser_ap_kwargs(definition)

    def _preprocess_base_ap_kwargs(self, kwargs):
        # Change argparse.ArgumentParser defaults
        kwargs.setdefault('allow_abbrev', False)
        kwargs.setdefault('formatter_class', HelpFormatter)
        kwargs.setdefault('argument_default', sargeparse.unset)

        if self._show_warnings and kwargs['allow_abbrev']:
            LOG.warning("Disabling 'allow_abbrev' is probably better to ensure consistent behavior")

        self._log_warning_if_elements_are_different_from_none(kwargs, 'prog', 'usage')

    def _preprocess_parser_ap_kwargs(self, kwargs):
        if 'help' in kwargs:
            raise TypeError("'help' parameter applies only to subcommands")

        self._log_warning_if_missing(kwargs, "Parser", 'description')

    def _preprocess_subcommand_ap_kwargs(self, kwargs):
        if not kwargs.get('name'):
            raise TypeError("Subcommand 'name' missing or invalid")

        self._log_warning_if_missing(kwargs, "subcommand '{}'".format(kwargs['name']), 'help')

        kwargs.setdefault('description', kwargs.get('help'))

        if self._has_positional_arguments:
            self._log_warning_parser_has_positional_arguments_and_subcommands()

    # ------ CLI argument parsing methods ------
    def _add_subcommands(self, parser, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            name = definition.pop('name')
            subcommand = Parser(
                definition,
                show_warnings=self._show_warnings,
                _subcommand=True,
            )

            # Create ArgumentParser instance and initialize
            parser.set_subparsers(**self.subparsers_kwargs)
            subparser = parser.add_parser(name, **subcommand.argument_parser_kwargs)
            subparser.set_defaults(**subcommand.default_kwargs)

            argument_list = subcommand._compile_argument_list()
            parser.add_arguments(*argument_list)

            subcommand._add_subcommands(subparser, *subcommand.subcommand_definitions)

    def _parse_cli_arguments(self, argv):
        argument_parser_kwargs = self.argument_parser_kwargs.copy()
        argument_parser_kwargs['argument_default'] = sargeparse.unset

        # Create ArgumentParser instance and initialize
        ap = ArgumentParser(**argument_parser_kwargs)
        parser = _ArgumentParserHelper(ap)
        parser.set_defaults(**self.default_kwargs)

        # Add global arguments first
        global_argument_list = self._compile_argument_list({'global': True})
        parser.add_arguments(*global_argument_list)

        # Replace help subcommand by --help at the end, makes it possible to use:
        # command help, command help subcommand, command help subcommand subsubcommand...
        if self.subcommand_definitions and self.help_subcommand and argv and argv[0] == 'help':
            argv.pop(0)
            argv.append('--help')

        # Parse global options first so they can be placed anywhere, unless the --help/-h flag is set
        parsed_args, rest = None, argv
        if '-h' not in rest and '--help' not in rest:
            parsed_args, rest = parser.parse_known_args(rest)

        # Add the rest of arguments
        argument_list = self._compile_argument_list({'global': False})
        parser.add_arguments(*argument_list)

        # Add subcommands
        self._add_subcommands(parser, *self.subcommand_definitions)
        if self.subcommand_definitions and self.help_subcommand:
            self._add_help_subcommand_definition(parser)

        # TODO
        # for command in commands.values():
        #    add_subcommands_to_description(command)

        # Finish parsing args
        parsed_args = parser.parse_args(rest, parsed_args)

        # Update _arguments
        self._argument_data['cli'].clear()
        self._argument_data['cli'].update(parsed_args.__dict__)

    def _add_help_subcommand_definition(self, parser):
        definition = {
            'name': 'help',
            'help': "show this message",
            'arguments': [
                {
                    'names': ['_help'],
                    'nargs': '?',
                    'metavar': '{} ...'.format(self.subparsers_kwargs['title'].upper()),
                    'help': None,
                },
            ],
        }

        self._preprocess_base_ap_kwargs(definition)
        self._preprocess_subcommand_ap_kwargs(definition)
        self._add_subcommands(parser, definition)

    def _set_arg_default_dict_from_cli_dict(self):
        for k, v in list(self._argument_data['cli'].items()):
            if v == sargeparse.unset:
                self._argument_data['cli'].pop(k)

                if self.argument_parser_kwargs['argument_default'] == sargeparse.suppress:
                    continue

                self._argument_data['arg_default'][k] = self.argument_parser_kwargs['argument_default']

    # ------ Additional argument sources' methods ------
    def _parse_envvars_and_defaults(self):
        for argument in self._argument_data:
            dest = argument.dest

            envvar = argument.get_value_from_envvar(default=sargeparse.unset)
            if envvar != sargeparse.unset:
                self._argument_data['environment'][dest] = envvar

            default = argument.get_default_value(default=sargeparse.unset)
            if default != sargeparse.unset:
                self._argument_data['defaults'][dest] = default

            self._argument_data['arg_default'][dest] = self.argument_parser_kwargs['argument_default']

        # TODO classify subcommands
        # for subcommand_definition in subcommand_definitions:
            # self._parse_envvars_and_defaults(subcommand_definition)

    def _parse_config(self, config):

        for argument in self._argument_data:
            dest = argument.dest

            config_value = argument.get_value_from_config(config, default=sargeparse.unset)
            if config_value != sargeparse.unset:
                self._argument_data['configuration'][dest] = config_value

            self._argument_data['arg_default'][dest] = self.argument_parser_kwargs['argument_default']

        # TODO classify subcommands
        # for subcommand_definition in subcommand_definitions:
            # self._parse_config(config, subcommand_definition)

    # ------ Logging helper methods ------
    def _log_warning_parser_has_positional_arguments_and_subcommands(self):
        if self._show_warnings:
            LOG.warning("Having subcommands and positional arguments simultaneously is probably a bad idea")

    def _log_warning_if_missing(self, dictionary, where, *keys):
        if self._show_warnings:
            msg = "Missing '%s' in %s. Please add something helpful, or set it to None to hide this warning"
            filtered_keys = [k for k in keys if k not in dictionary]

            for k in filtered_keys:
                LOG.warning(msg, k, where)
                dictionary[k] = 'WARNING: MISSING {} MESSAGE'.format(k.upper())

    def _log_warning_if_elements_are_different_from_none(self, dictionary, *keys):
        if self._show_warnings:
            msg = "The default value of '%s' is probably better than: '%s'"
            filtered_dict = {k: v for k, v in dictionary.items() if k in keys and v is not None}

            for k, v in filtered_dict.items():
                LOG.warning(msg, k, v)

    # ------ Argument methods ------
    def _compile_argument_list(self, schema=None):
        schema = schema or {}
        argument_list = []
        mutexes = {}
        groups = {}

        arguments = []
        for argument in [arg for arg in self.arguments if arg.validate_schema(schema)]:
            arguments.append(argument)

        # Make groups / mutex_groups from plain argument definition list
        for argument in arguments:
            # definition = argument.get_definition_without_custom_parameters()
            target = argument_list

            # Add group to 'arguments' if not there already and point target to it
            group = argument.pop_parameter('group', None)
            if group:
                if group not in groups:
                    groups[group] = {
                        '_type': 'group',
                        'title': group,
                        'description': None,
                        'arguments': [],
                    }
                    description = self.group_descriptions.get(group)
                    groups[group]['description'] = description
                    target.append(groups[group])

                target = groups[group]['arguments']

            # Add mutex to 'arguments' if not there already and point target to it
            mutex = argument.pop_parameter('mutex', None)
            if mutex:
                if mutex not in mutexes:
                    mutexes[mutex] = {
                        '_type': 'mutex',
                        'required': True,
                        'arguments': [],
                    }
                    target.append(mutexes[mutex])

                target = mutexes[mutex]['arguments']

            # Add argument definition to whatever target is pointing at
            target.append(argument)

        # Set 'required' to False in mutexes when all of its arguments have 'required': False
        for mutex in mutexes.values():
            for argument in mutex['arguments']:
                if not argument.validate_schema({'required': False}):
                    break
            else:
                mutex['required'] = False

        yield from argument_list


class _ArgumentParserHelper:
    def __init__(self, parser):
        self.parser = parser

    def add_arguments(self, *definition_list):
        for definition in definition_list:
            # FIXME
            if isinstance(definition, Argument):
                self._add_argument(definition, self.parser)
                continue

            definition = definition.copy()

            argument_type = definition.pop('_type', None)
            if argument_type == 'group':
                self._add_group(definition, self.parser)
            elif argument_type == 'mutex':
                self._add_mutex(definition, self.parser)
            else:
                self._add_argument(definition, self.parser)

    def _add_group(self, obj, dest):
        arguments = obj.pop('arguments')
        group = dest.add_argument_group(**obj)

        # FIXME
        for argument in arguments:
            if not isinstance(argument, Argument):  # TODO change this eventually by mutex class
                argument.pop('_type', None)
                self._add_mutex(argument, group)
            else:
                self._add_argument(argument, group)

    def _add_mutex(self, obj, dest):
        arguments = obj.pop('arguments')
        mutex = dest.add_mutually_exclusive_group(**obj)

        for argument in arguments:
            self._add_argument(argument, mutex)

    @staticmethod
    def _add_argument(argument, dest):
        definition = argument.get_definition_without_custom_parameters()
        dest.add_argument(*argument.names, **definition)

    def get_subparsers(self):
        return self.parser._subparsers._group_actions[0]

    def set_subparsers(self, **kwargs):
        if not self.parser._subparsers:
            self.parser.add_subparsers(**kwargs)

    def add_parser(self, name, **kwargs):
        subparsers = self.get_subparsers()
        subparser = subparsers.add_parser(name, **kwargs)
        return _ArgumentParserHelper(subparser)

    def set_defaults(self, **kwargs):
        self.parser.set_defaults(**kwargs)

    def parse_args(self, *args, **kwargs):
        return self.parser.parse_args(*args, **kwargs)

    def parse_known_args(self, *args, **kwargs):
        return self.parser.parse_known_args(*args, **kwargs)

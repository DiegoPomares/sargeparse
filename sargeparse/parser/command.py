import sys
import collections

import sargeparse.consts

from sargeparse.parser.context_manager import CheckKwargs
from sargeparse.custom import ArgumentParser

from sargeparse.parser._parser import Parser

from sargeparse.parser._argument import Argument
from sargeparse.parser._group import ArgumentGroup, MutualExclussionGroup


class _BaseMixin:
    def __init__(self, definition, **kwargs):
        raise NotImplementedError()

    def add_arguments(self, *definitions):
        self._parser.add_arguments(*definitions)

    def add_subcommand(self, subcommand):
        if isinstance(subcommand, dict):
            self._add_subcommand_definition(subcommand)
        else:
            self._add_subcommand_object(subcommand)

    def _add_subcommand_definition(self, definition):
        raise NotImplementedError()

    def _add_subcommand_object(self, subcommand):
        self._parser.add_subparsers(subcommand._parser)

    def add_subcommands(self, *definitions):
        for definition in definitions:
            self.add_subcommand(definition)

    def add_defaults(self, **kwargs):
        self._parser.add_set_defaults_kwargs(**kwargs)

    def add_group_descriptions(self, **kwargs):
        self._parser.add_group_descriptions(**kwargs)


class SubCommand(_BaseMixin):
    # pylint: disable=super-init-not-called
    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        with CheckKwargs(kwargs) as k:
            self._show_warnings = k.pop('show_warnings', True)

        self._custom_parameters = {
            'arguments': definition.pop('arguments', []),
            'subcommands': definition.pop('subcommands', []),
        }

        self._parser = Parser(
            definition,
            show_warnings=self._show_warnings,
            subcommand=True,
        )

        self.add_arguments(*self._custom_parameters['arguments'])
        self.add_subcommands(*self._custom_parameters['subcommands'])

    def _add_subcommand_definition(self, definition):
        subcommand = SubCommand(
            definition,
            show_warnings=self._show_warnings,
        )
        return self._add_subcommand_object(subcommand)


class Command(_BaseMixin):
    _default_precedence = ['cli', 'environment', 'configuration', 'defaults']

    # pylint: disable=super-init-not-called
    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        with CheckKwargs(kwargs) as k:
            self._show_warnings = k.pop('show_warnings', True)

        self._custom_parameters = {
            'help_subcommand': definition.pop('help_subcommand', True),
            'arguments': definition.pop('arguments', []),
            'subcommands': definition.pop('subcommands', []),
        }

        self._parser = Parser(
            definition,
            show_warnings=self._show_warnings,
            subcommand=False,
        )
        self.help_subcommand = self._custom_parameters['help_subcommand']
        self.add_arguments(*self._custom_parameters['arguments'])
        self.add_subcommands(*self._custom_parameters['subcommands'])

        # TODO better naming, improve precedence thing
        self._argument_data = None
        self._parsed_data = None

        precedence = ['override'] + self._default_precedence + ['arg_default']
        self._argument_data = {k: {} for k in precedence}
        self._parsed_data = collections.ChainMap()
        self.set_precedence()

    def _add_subcommand_definition(self, definition):
        subcommand = SubCommand(
            definition,
            show_warnings=self._show_warnings,
        )
        return self._add_subcommand_object(subcommand)

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
        argument_parser_kwargs = self._parser.argument_parser_kwargs.copy()
        argument_parser_kwargs['argument_default'] = sargeparse.unset

        # Create ArgumentParser instance and initialize
        ap = ArgumentParser(**argument_parser_kwargs)
        parser = _ArgumentParserHelper(ap)
        parser.set_defaults(**self._parser.set_defaults_kwargs)

        # Add global arguments first
        global_arguments = self._parser.compile_argument_list({'global': True})
        parser.add_arguments(*global_arguments)

        # Replace help subcommand by --help at the end, makes it possible to use:
        # command help, command help subcommand, command help subcommand subsubcommand...
        if self._parser.subparsers and self.help_subcommand and argv and argv[0] == 'help':
            argv.pop(0)
            argv.append('--help')

        # Parse global options first so they can be placed anywhere, unless the --help/-h flag is set
        parsed_args, rest = None, argv
        if '-h' not in rest and '--help' not in rest:
            parsed_args, rest = parser.parse_known_args(rest)

        # Add the rest of arguments
        arguments = self._parser.compile_argument_list({'global': False})
        parser.add_arguments(*arguments)

        # Add subcommands TODO
        #self._add_subcommands(parser, *self.subcommand_definitions)
        #if self.subcommand_definitions and self.help_subcommand:
        #    self._add_help_subcommand_definition(parser)

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


class _ArgumentParserHelper:
    def __init__(self, parser):
        self.parser = parser

    def add_arguments(self, *objs):
        for obj in objs:
            if isinstance(obj, ArgumentGroup):
                self._add_argument_group(obj, dest=self.parser)

            elif isinstance(obj, MutualExclussionGroup):
                self._add_mutex_group(obj, dest=self.parser)

            elif isinstance(obj, Argument):
                self._add_argument(obj, dest=self.parser)

            else:
                raise RuntimeError()

    def _add_argument_group(self, argument_group, *, dest):
        group = dest.add_argument_group(
            title=argument_group.title,
            description=argument_group.description,
        )

        for obj in argument_group.arguments:
            if isinstance(obj, MutualExclussionGroup):
                self._add_mutex_group(obj, dest=group)

            elif isinstance(obj, Argument):
                self._add_argument(obj, dest=group)

    def _add_mutex_group(self, mutex_group, *, dest):
        group = dest.add_mutually_exclusive_group(
            required=mutex_group.is_required(),
        )

        for argument in mutex_group.arguments:
            self._add_argument(argument, dest=group)

    @staticmethod
    def _add_argument(argument, *, dest):
        dest.add_argument(
            *argument.names,
            **argument.add_argument_kwargs,
        )

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

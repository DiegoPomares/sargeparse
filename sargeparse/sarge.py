import sys

import sargeparse.consts

from sargeparse.context_manager import check_kwargs
from sargeparse.custom import ArgumentParser

from sargeparse._parser import (
    Argument,
    ArgumentGroup,
    MutualExclussionGroup,
    ArgumentValues,
    Parser,
)


class SubCommand:
    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        with check_kwargs(kwargs):
            self._show_warnings = kwargs.pop('show_warnings', True)
            self._main_command = kwargs.pop('_main_command', False)

        self._custom_parameters = {
            'arguments': definition.pop('arguments', []),
            'subcommands': definition.pop('subcommands', []),
        }

        self._parser = Parser(
            definition,
            show_warnings=self._show_warnings,
            main_command=self._main_command,
        )

        self.add_arguments(*self._custom_parameters['arguments'])
        self.add_subcommands(*self._custom_parameters['subcommands'])

    def _add_subcommand_definition(self, definition):
        subcommand = SubCommand(
            definition,
            show_warnings=self._show_warnings,
        )
        return self._add_subcommand_object(subcommand)

    def _add_subcommand_object(self, subcommand):
        self._parser.add_subparsers(subcommand._parser)
        return subcommand

    def add_arguments(self, *definitions):
        self._parser.add_arguments(*definitions)

    def add_defaults(self, defaults):
        self._parser.add_set_defaults_kwargs(defaults)

    def add_group_descriptions(self, descriptions):
        self._parser.add_group_descriptions(descriptions)

    def add_subcommand(self, subcommand):
        if isinstance(subcommand, dict):
            return self._add_subcommand_definition(subcommand)

        return self._add_subcommand_object(subcommand)

    def add_subcommands(self, *subcommands):
        for subcommand in subcommands:
            self.add_subcommand(subcommand)


class Sarge(SubCommand):
    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        self._custom_parameters = {
            'help_subcommand': definition.pop('help_subcommand', True),
        }

        self.help_subcommand = self._custom_parameters['help_subcommand']

        kwargs['_main_command'] = True
        super().__init__(definition, **kwargs)

        precedence = kwargs.pop('precedence', None)
        self._data = ArgumentValues(self._parser, precedence)

    def parse(self, argv=None, read_config=None):
        argv = argv or sys.argv[1:]

        self._data.clear_all()

        cli_args = self._parse_cli_arguments(argv)
        self._data.cli.update(cli_args)
        self._data._remove_unset_from_data_sources_cli()
        self._data._move_defaults_from_data_sources_cli()

        self._data._parse_envvars_and_defaults()

        # Config callback
        if read_config:
            config = read_config(self._data)
            self._data._parse_config(config)

        self._data._parse_callbacks()
        self._data._remove_parser_key_from_data_sources_cli()

        return self._data

    def _parse_cli_arguments(self, argv):
        argument_parser_kwargs = self._parser.argument_parser_kwargs.copy()
        argument_parser_kwargs['argument_default'] = sargeparse.unset

        # Create ArgumentParser instance and initialize
        ap = ArgumentParser(**argument_parser_kwargs)
        apw = _ArgumentParserWrapper(ap)
        apw.set_defaults(**self._parser.get_set_default_kwargs())

        # Add global arguments first
        global_arguments = self._parser.compile_argument_list({'global': True})
        apw.add_arguments(*global_arguments)

        # Replace help subcommand by --help at the end, makes it possible to use:
        # command help, command help subcommand, command help subcommand subsubcommand...
        if self._parser.subparsers and self.help_subcommand and argv and argv[0] == 'help':
            argv.pop(0)
            argv.append('--help')

        # Parse global options first so they can be placed anywhere, unless the --help/-h flag is set
        parsed_args, rest = None, argv
        if '-h' not in rest and '--help' not in rest:
            parsed_args, rest = apw.parse_known_args(rest)

        # Add the rest of arguments
        arguments = self._parser.compile_argument_list({'global': False})
        apw.add_arguments(*arguments)

        # Add subcommands
        apw.add_subcommands(*self._parser.subparsers)
        if self._parser.subparsers and self.help_subcommand:
            apw.add_subcommands(self._make_help_subparser())

        # TODO subcommand usage in description flag

        # Finish parsing args
        parsed_args = apw.parse_args(rest, parsed_args)

        return parsed_args.__dict__

    def _make_help_subparser(self):
        parser = Parser(
            {'name': 'help', 'help': "show this message"},
            show_warnings=self._show_warnings,
            main_command=False,
        )
        parser.add_arguments({
            'names': ['_help'],
            'nargs': '?',
            'metavar': '{} ...'.format(self._parser.add_subparsers_kwargs['title'].upper()),
            'help': None,
        })

        return parser


class _ArgumentParserWrapper:
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
            **argument.add_argument_kwargs
        )

    def add_subcommands(self, *subparsers):
        for subparser in subparsers:

            self.setup_subparsers(**subparser.add_subparsers_kwargs)

            new_parser = self.add_parser(
                subparser.name,
                **subparser.argument_parser_kwargs
            )

            new_parser.set_defaults(**subparser.get_set_default_kwargs())

            arguments = subparser.compile_argument_list()
            new_parser.add_arguments(*arguments)

            new_parser.add_subcommands(*subparser.subparsers)

    def get_subparsers_obj(self):
        return self.parser._subparsers._group_actions[0]

    def setup_subparsers(self, **kwargs):
        if not self.parser._subparsers:
            self.parser.add_subparsers(**kwargs)

    def add_parser(self, name, **kwargs):
        subparsers = self.get_subparsers_obj()
        subparser = subparsers.add_parser(name, **kwargs)
        return _ArgumentParserWrapper(subparser)

    def set_defaults(self, **kwargs):
        self.parser.set_defaults(**kwargs)

    def parse_args(self, *args, **kwargs):
        return self.parser.parse_args(*args, **kwargs)

    def parse_known_args(self, *args, **kwargs):
        return self.parser.parse_known_args(*args, **kwargs)

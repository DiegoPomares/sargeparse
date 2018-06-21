import sys
import textwrap
import logging

import sargeparse.consts

from sargeparse.context_manager import check_kwargs
from sargeparse.custom import HelpFormatter
from sargeparse.version import python_version

from sargeparse._parser.argument import Argument
from sargeparse._parser.group import ArgumentGroup, MutualExclussionGroup

LOG = logging.getLogger(__name__)


class Parser:
    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        with check_kwargs(kwargs):
            self.main_command = kwargs.pop('main_command')
            self._show_warnings = kwargs.pop('show_warnings')

        self.arguments = []
        self.subparsers = []

        self.custom_parameters = {
            'callback': definition.pop('callback', None),
            'add_usage_to_parent_command_desc': definition.pop('add_usage_to_parent_command_desc', False),
            'group_descriptions': definition.pop('group_descriptions', {}),
            'print_help_and_exit_if_last': definition.pop('print_help_and_exit_if_last', False),
            'add_help': definition.pop('add_help', True),
            'defaults': definition.pop('defaults', {}),
            'subparser': definition.pop('subparser', {}),
        }

        self._prefix_chars = definition.get('prefix_chars', '-')
        self._has_positional_arguments = False

        self.name = None
        self.callback = self.custom_parameters['callback']
        self.add_usage_to_parent_command_desc = self.custom_parameters['add_usage_to_parent_command_desc']
        self.set_defaults_kwargs = self.custom_parameters['defaults']
        self.add_subparsers_kwargs = self.custom_parameters['subparser']
        self.argument_parser_kwargs = definition

        self._process_argument_parser_kwargs()
        self._process_add_subparsers_kwargs()
        self._process_custom_parameters()

    def add_arguments(self, *definitions):
        for definition in definitions:
            argument = Argument(
                definition,
                show_warnings=self._show_warnings,
                prefix_chars=self._prefix_chars,
                main_command=self.main_command,
            )
            self.arguments.append(argument)

            if argument.is_positional():
                self._has_positional_arguments = True

        self._log_warning_if_command_has_positional_arguments_and_subparsers()

    def add_subparsers(self, *subparsers):
        for subparser in subparsers:
            self.subparsers.append(subparser)

        self._log_warning_if_command_has_positional_arguments_and_subparsers()

    def add_set_defaults_kwargs(self, defaults):
        self.custom_parameters['defaults'].update(defaults)

    def parser_key(self):
        return '_parser_{}'.format(id(self))

    def get_set_default_kwargs(self):
        kwargs = {}

        kwargs['defaults'] = self.set_defaults_kwargs

        if self.callback:
            kwargs['callback'] = self.callback

        return {self.parser_key(): kwargs}

    def add_group_descriptions(self, descriptions):
        self.custom_parameters['group_descriptions'].update(descriptions)

    def _process_argument_parser_kwargs(self):
        self._process_common_argument_parser_kwargs()

        if self.main_command:
            self._process_argument_parser_kwargs_for_main_command()
        else:
            self._process_argument_parser_kwargs_for_subcommand()

    def _process_common_argument_parser_kwargs(self):
        self.argument_parser_kwargs.setdefault('formatter_class', HelpFormatter)
        self.argument_parser_kwargs.setdefault('argument_default', sargeparse.unset)

        if 'description' in self.argument_parser_kwargs:
            desc = textwrap.dedent(self.argument_parser_kwargs['description'])
            self.argument_parser_kwargs['description'] = desc

        # Help flag is handled internally
        self.argument_parser_kwargs['add_help'] = False

        if python_version('<3.5'):  # Unsupported
            if 'allow_abbrev' in self.argument_parser_kwargs:
                raise ValueError("'allow_abbrev' is not supported in Python < 3.5")

        self._log_warning_if_elements_are_different_from_none(self.argument_parser_kwargs, 'prog', 'usage')

    def _process_argument_parser_kwargs_for_main_command(self):
        if 'help' in self.argument_parser_kwargs:
            raise TypeError("'help' parameter applies only to subcommands")

        self._log_warning_if_missing(self.argument_parser_kwargs, "Parser", 'description')

    def _process_argument_parser_kwargs_for_subcommand(self):
        self.name = self.argument_parser_kwargs.pop('name', None)
        if not self.name:
            raise TypeError("Subcommand 'name' missing or invalid")

        self._log_warning_if_missing(
            self.argument_parser_kwargs,
            "subcommand '{}'".format(self.name),
            'help',
        )

        self.argument_parser_kwargs.setdefault(
            'description',
            self.argument_parser_kwargs.get('help')
        )

    def _process_add_subparsers_kwargs(self):
        self._log_warning_if_elements_are_different_from_none(self.add_subparsers_kwargs, 'prog', 'help')

        self.add_subparsers_kwargs.setdefault('title', 'subcommands')
        self.add_subparsers_kwargs.setdefault('metavar', 'SUBCOMMAND')
        self.add_subparsers_kwargs.setdefault('help', None)

    def _process_custom_parameters(self):
        self._process_common_custom_parameters()

        if self.main_command:
            self._process_custom_parameters_for_main_command()
        else:
            self._process_custom_parameters_for_subcommand()

    def _process_common_custom_parameters(self):
        if self.callback and self.custom_parameters['print_help_and_exit_if_last']:
            raise ValueError("'callback' and 'print_help_and_exit_if_last' are mutually exclusive")

        if self.custom_parameters['print_help_and_exit_if_last']:
            self.callback = self._make_print_help_and_exit_if_last_function()

        if not self.callback:
            self.callback = (lambda ctx: ctx.return_value)

        if not callable(self.callback):
            raise TypeError("'callback' is not callable")

        self.callback.parser = self

    def _process_custom_parameters_for_main_command(self):
        if self.add_usage_to_parent_command_desc:
            raise TypeError("'add_usage_to_parent_command_desc' parameter applies only to subcommands")

    def _process_custom_parameters_for_subcommand(self):
        pass

    @staticmethod
    def _make_print_help_and_exit_if_last_function():
        def fn(ctx):
            if not ctx.last:
                return None

            print(ctx.parser.help, file=sys.stderr)
            return sargeparse.die(0)

        return fn

    def _log_warning_if_command_has_positional_arguments_and_subparsers(self):
        if self._show_warnings and self._has_positional_arguments and self.subparsers:
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

    def _make_help_argument(self):
        definition = {
            'names': ['-h', '--help'],
            'help': 'show this help message and exit',
            'action': 'help',
        }

        return Argument(
            definition,
            show_warnings=self._show_warnings,
            prefix_chars=self._prefix_chars,
            main_command=self.main_command,
        )

    def _validate_mutex_groups(self):
        mutex_groups = {a.mutex_group for a in self.arguments if a.mutex_group}

        for mutex in mutex_groups:
            properties = {
                'required': {a.validate_schema({'required': True}) for a in self.arguments if a.mutex_group == mutex},
                'global': {a.validate_schema({'global': True}) for a in self.arguments if a.mutex_group == mutex},
                'group': {a.group for a in self.arguments if a.mutex_group == mutex},
            }

            for k, v in properties.items():
                if len(v) > 1:
                    msg = "'{}' property must have the same value in all mutex group arguments".format(k)
                    raise ValueError(msg)

    def compile_argument_list(self, schema=None):
        schema = schema or {}
        all_arguments = self.arguments.copy()
        argument_list = []
        mutexes = {}
        groups = {}

        # Verify mutex_group conditions are right
        self._validate_mutex_groups()

        # Add help
        if self.custom_parameters['add_help']:
            all_arguments.append(self._make_help_argument())

        # Filter according to schema
        arguments = [a for a in all_arguments if a.validate_schema(schema)]

        # Make groups / mutex_groups argument list
        for argument in arguments:
            target = argument_list

            group = argument.group
            if group:
                # Add group to 'argument_list' if not there already
                if group not in groups:
                    groups[group] = ArgumentGroup(
                        group,
                        description=self.custom_parameters['group_descriptions'].get(group)
                    )
                    target.append(groups[group])

                target = groups[group].arguments

            mutex = argument.mutex_group
            if mutex:
                # Add mutex to 'argument_list' if not there already
                if mutex not in mutexes:
                    mutexes[mutex] = MutualExclussionGroup(
                        required=argument.add_argument_kwargs.get('required', False)
                    )
                    target.append(mutexes[mutex])

                target = mutexes[mutex].arguments

            # Add argument definition to whatever target is pointing at
            target.append(argument)

        yield from argument_list

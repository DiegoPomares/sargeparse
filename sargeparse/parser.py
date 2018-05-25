import os
import sys
import logging
import collections

import sargeparse.consts

from sargeparse.custom import PathDict, ArgumentParser, HelpFormatter

LOG = logging.getLogger(__name__)


class Parser:
    _default_precedence = ['cli', 'environment', 'configuration', 'defaults']
    _custom_arg_params = ['shared', 'envvar', 'default', 'config_path']
    _custom_ap_params = ['help_subcommand']

    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        self._show_warnings = kwargs.pop('show_warnings', True)
        self._subcommand = kwargs.pop('_subcommand', False)
        self._prefix_chars = definition.get('prefix_chars', '-')

        self._arguments = None
        self._parsed_data = None
        self._has_positional_arguments = False

        self.argument_definitions = []
        self.subcommand_definitions = []
        self.subparsers_kwargs = {}

        self.add_arguments(*definition.pop('arguments', []))
        self.add_subcommands(*definition.pop('subcommands', []))
        self.config_subparsers(**definition.pop('subparsers', {}))
        self.default_kwargs = definition.pop('default', {})
        self.argument_parser_kwargs = definition

        if not self._subcommand:
            self.help_subcommand = definition.pop('help_subcommand', True)
            self._preprocess_base_ap_kwargs(self.argument_parser_kwargs)
            self._preprocess_parser_ap_kwargs(self.argument_parser_kwargs)

            precedence = ['override'] + self._default_precedence + ['arg_default']
            self._arguments = {k: {} for k in precedence}
            self._parsed_data = collections.ChainMap()
            self.set_precedence()

    ################################################################################################
    # User methods
    def add_arguments(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            self._preprocess_argument_definition(definition)
            self.argument_definitions.append(definition)

    def add_subcommands(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            self._preprocess_base_ap_kwargs(definition)
            self._preprocess_subcommand_ap_kwargs(definition)

            self.subcommand_definitions.append(definition)

    def config_subparsers(self, **kwargs):
        kwargs = kwargs.copy()

        self._log_warning_if_elements_are_different_from_none(kwargs, 'prog', 'help')

        kwargs.setdefault('title', 'subcommands')
        kwargs.setdefault('metavar', 'SUBCOMMAND')
        kwargs.setdefault('help', None)

        self.subparsers_kwargs = kwargs

    def set_defaults(self, **kwargs):
        kwargs = kwargs.copy()
        self.default_kwargs = kwargs

    def parse(self, argv=None, read_config=None):
        argv = argv or sys.argv[1:]

        self._parse_cli_arguments(argv)
        self._set_arg_default_dict_from_cli_dict()
        self._parse_envvars_and_defaults()

        # Callback
        if read_config:
            config = PathDict(read_config(self._parsed_data))
            self._parse_config(config)
        else:
            self._arguments['configuration'].clear()

        return dict(self._parsed_data), self._parsed_data
        # return self._parsed_data

    def set_precedence(self, precedence=None):
        precedence = precedence or self._default_precedence

        difference = set(self._default_precedence).symmetric_difference(set(precedence))
        if difference:
            msg = "Precedence must contain all and only these elements: {}"
            raise TypeError(msg.format(self._default_precedence))

        precedence = ['override'] + precedence + ['arg_default']
        self._parsed_data.maps = [self._arguments[k] for k in precedence]

    ################################################################################################
    # Preprocessors
    def _preprocess_argument_definition(self, definition):
        self._preprocess_base_argument_definition(definition)

        if self._subcommand:
            self._preprocess_subcommand_argument_definition(definition)
        else:
            self._preprocess_parser_argument_definition(definition)

    def _preprocess_base_argument_definition(self, definition):
        self._log_warning_if_missing(definition, "argument '{}'".format(definition['names']), 'help')

        if not definition.get('names'):
            raise TypeError("Argument 'names' missing or invalid")

        dest = self._make_dest_from_names(definition['names'])

        if self._is_argument_positional(definition):

            # argparse will raise an exception if the argument is positional and 'dest' is set
            if 'dest' in definition:
                msg = "Positional arguments cannot have a 'dest', remove it from the definition: '{}'".format(
                    definition['dest']
                )
                raise TypeError(msg)

            self._has_positional_arguments = True

            if self.subcommand_definitions:
                self._log_warning_parser_has_positional_arguments_and_subcommands()

        else:  # argument is optional

            if 'dest' not in definition:
                definition['dest'] = dest

    def _preprocess_parser_argument_definition(self, definition):
        definition.setdefault('shared', False)

        if definition['shared'] and self._is_argument_positional(definition):
            raise TypeError("Positional arguments cannot be 'shared': '{}'".format(definition['names'][0]))

    @staticmethod
    def _preprocess_subcommand_argument_definition(definition):
        if 'shared' in definition:
            raise TypeError("'shared' arguments are not available in subcommands")

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

        if 'description' not in kwargs:
            kwargs['description'] = kwargs.get('help')

        if self._has_positional_arguments:
            self._log_warning_parser_has_positional_arguments_and_subcommands()

    ################################################################################################
    # Internal methods
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

            arguments = subcommand._get_arguments()
            arguments = subcommand._pop_elements_from_dicts(arguments, *self._custom_arg_params)
            subparser.add_arguments(*arguments)

            subcommand._add_subcommands(subparser, *subcommand.subcommand_definitions)

    def _parse_cli_arguments(self, argv):
        argument_parser_kwargs = self.argument_parser_kwargs.copy()
        argument_parser_kwargs['argument_default'] = sargeparse.unset

        # Create ArgumentParser instance and initialize
        ap = ArgumentParser(**argument_parser_kwargs)
        parser = _ArgumentParserHelper(ap)
        parser.set_defaults(**self.default_kwargs)

        # Add shared arguments first
        shared_arguments = self._get_arguments(shared=True)
        shared_arguments = self._pop_elements_from_dicts(shared_arguments, *self._custom_arg_params)
        parser.add_arguments(*shared_arguments)

        # Replace help subcommand by --help at the end, makes it possible to use:
        # command help, command help subcommand, command help subcommand subsubcommand...
        if self.subcommand_definitions and self.help_subcommand and argv and argv[0] == 'help':
            argv.pop(0)
            argv.append('--help')

        # Parse shared options first so they can be placed anywhere, unless the --help/-h flag is set
        parsed_args, rest = None, argv
        if '-h' not in rest and '--help' not in rest:
            parsed_args, rest = parser.parse_known_args(rest)

        # Add the rest of arguments
        arguments = self._get_arguments(shared=False)
        arguments = self._pop_elements_from_dicts(arguments, *self._custom_arg_params)
        parser.add_arguments(*arguments)

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
        self._arguments['cli'].clear()
        self._arguments['cli'].update(parsed_args.__dict__)

    def _set_arg_default_dict_from_cli_dict(self):
        for k, v in list(self._arguments['cli'].items()):
            if v == sargeparse.unset:
                self._arguments['cli'].pop(k)

                if self.argument_parser_kwargs['argument_default'] == sargeparse.suppress:
                    continue

                self._arguments['arg_default'][k] = self.argument_parser_kwargs['argument_default']

    def _get_argument_and_subcommand_definitions(self, definition=None):
        if not definition:
            argument_definitions = self.argument_definitions
            subcommand_definitions = self.subcommand_definitions
        else:
            argument_definitions = definition.get('arguments', [])
            subcommand_definitions = definition.get('subcommand_definitions', [])

        return argument_definitions, subcommand_definitions

    def _parse_envvars_and_defaults(self, definition=None):
        argument_definitions, subcommand_definitions = self._get_argument_and_subcommand_definitions(definition)

        for argument_definition in argument_definitions:
            dest = self._make_dest_from_names(argument_definition['names'])

            if 'envvar' in argument_definition:
                envvar = os.environ.get(argument_definition['envvar'], sargeparse.unset)
                if envvar != sargeparse.unset:
                    self._arguments['environment'][dest] = envvar
                else:
                    self._arguments['arg_default'][dest] = self.argument_parser_kwargs['argument_default']

            if 'default' in argument_definition:
                default = argument_definition['default']
                self._arguments['defaults'][dest] = default

        for subcommand_definition in subcommand_definitions:
            self._parse_envvars_and_defaults(subcommand_definition)

    def _parse_config(self, config, definition=None):
        argument_definitions, subcommand_definitions = self._get_argument_and_subcommand_definitions(definition)

        for argument_definition in argument_definitions:
            dest = self._make_dest_from_names(argument_definition['names'])

            if 'config_path' in argument_definition:
                config_value = config.get_path(argument_definition['config_path'], sargeparse.unset)
                if config_value != sargeparse.unset:
                    self._arguments['configuration'][dest] = config_value
                else:
                    self._arguments['arg_default'][dest] = self.argument_parser_kwargs['argument_default']

        for subcommand_definition in subcommand_definitions:
            self._parse_config(config, subcommand_definition)

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

    def _make_dest_from_names(self, names):
        '''Get the 'dest' parameter based on the argument names'''

        dest = None

        for name in names:
            if name[0] in self._prefix_chars and not dest:
                dest = name[1:]

            if name[0] not in self._prefix_chars:
                dest = name
                break

            if name[0] in self._prefix_chars and name[0] == name[1]:
                dest = name[2:]
                break

        return dest.replace('-', '_')

    def _is_argument_positional(self, definition):
        '''Return whether or not an argument is 'positional', being 'optional' the alternative'''

        return definition['names'][0][0] not in self._prefix_chars

    @staticmethod
    def _check_argument_properties(argument, **schema):
        '''Return True if the argument satisfies the schema'''

        for k, v in schema.items():
            # Special cases
            if v == sargeparse.unset:  # Property wasn't set in argument schema
                if k not in argument:
                    continue
                else:
                    return False

            if v == sargeparse.isset:  # Property was set in argument schema
                if k in argument:
                    continue
                else:
                    return False

            if v == sargeparse.eval_true:  # Property evaluates to True
                if argument.get(k, False):
                    continue
                else:
                    return False

            if v == sargeparse.eval_false:  # Property evaluates to False
                if not argument.get(k, True):
                    continue
                else:
                    return False

            # Standard case, property in argument equals some value
            if k in argument and argument[k] == v:  # TODO: verify this isnt flaky
                continue
            else:
                return False

        return True

    def _get_arguments(self, **schema):
        '''Return arguments that match a schema (see _check_argument_properties)'''

        for argument in self.argument_definitions:
            if self._check_argument_properties(argument, **schema):
                yield argument

    @staticmethod
    def _pop_elements_from_dicts(dicts, *key_list):
        '''Return a copy of a dict without the elements from key_list'''

        for dictionary in dicts:
            dictionary = dictionary.copy()

            for key in key_list:
                dictionary.pop(key, None)

            yield dictionary

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


class _ArgumentParserHelper:
    def __init__(self, parser):
        self.parser = parser

    def add_arguments(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            names = definition.pop('names')
            self.parser.add_argument(*names, **definition)

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


'''
def add_subcommands_to_description(command):
    if not command._subparsers:
        return

    command.description += '\n\n'
    for action, parser in command._subparsers._group_actions[0].choices.items():
        usage = parser.format_usage()[7:]
        command.description += usage
'''

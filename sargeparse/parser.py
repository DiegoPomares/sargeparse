import os
import sys
import logging
import collections

import sargeparse.consts

from sargeparse.custom import EZObject, PathDict, ArgumentParser, HelpFormatter

LOG = logging.getLogger(__name__)


class Parser:
    _default_precedence = ['cli', 'environment', 'configuration', 'defaults']
    _custom_arg_params = ['default', 'global', 'envvar', 'config_path']
    _custom_ap_params = ['help_subcommand']

    def __init__(self, definition, **kwargs):
        definition = definition.copy()
        self._ = EZObject()

        self._.show_warnings = kwargs.pop('show_warnings', True)
        self._.subcommand = kwargs.pop('_subcommand', False)
        self._.prefix_chars = definition.get('prefix_chars', '-')

        self._.arguments = None
        self._.parsed_data = None
        self._.has_positional_arguments = False

        self.argument_definitions = []
        self.subcommand_definitions = []
        self.subparsers_kwargs = {}
        self.add_arguments(*definition.pop('arguments', []))
        self.add_subcommands(*definition.pop('subcommands', []))
        self.config_subparsers(**definition.pop('subparsers', {}))

        self.group_descriptions = definition.pop('group_descriptions', {})
        self.default_kwargs = definition.pop('defaults', {})
        self.argument_parser_kwargs = definition

        if not self._.subcommand:
            self.help_subcommand = definition.pop('help_subcommand', True)
            self._preprocess_ap_kwargs(self.argument_parser_kwargs, subcommand=False)

            precedence = ['override'] + self._default_precedence + ['arg_default']
            self._.arguments = {k: {} for k in precedence}
            self._.parsed_data = collections.ChainMap()
            self.set_precedence()

    # ------ User methods ------
    def add_arguments(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            self._preprocess_argument_definition(definition)
            self.argument_definitions.append(definition)

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
            config = PathDict(read_config(self._.parsed_data))
            self._parse_config(config)
        else:
            self._.arguments['configuration'].clear()

        return self._.parsed_data

    def set_precedence(self, precedence=None):
        precedence = precedence or self._default_precedence

        difference = set(self._default_precedence).symmetric_difference(set(precedence))
        if difference:
            msg = "Precedence must contain all and only these elements: {}"
            raise TypeError(msg.format(self._default_precedence))

        precedence = ['override'] + precedence + ['arg_default']
        self._.parsed_data.maps = [self._.arguments[k] for k in precedence]

    # ------ Argument definition pre-processors ------
    def _preprocess_argument_definition(self, definition):
        self._preprocess_base_argument_definition(definition)

        if self._.subcommand:
            self._preprocess_subcommand_argument_definition(definition)
        else:
            self._preprocess_parser_argument_definition(definition)

    def _preprocess_base_argument_definition(self, definition):
        self._log_warning_if_missing(definition, "argument '{}'".format(definition['names']), 'help')

        if not definition.get('names'):
            raise TypeError("Argument 'names' missing or invalid")

        dest = self._make_dest_from_argument_names(definition['names'])

        if self._is_argument_positional(definition):

            # argparse will raise an exception if the argument is positional and 'dest' is set
            if 'dest' in definition:
                msg = "Positional arguments cannot have a 'dest', remove it from the definition: '{}'".format(
                    definition['dest']
                )
                raise TypeError(msg)

            self._.has_positional_arguments = True

            if self.subcommand_definitions:
                self._log_warning_parser_has_positional_arguments_and_subcommands()

        else:  # argument is optional
            definition.setdefault('dest', dest)

    def _preprocess_parser_argument_definition(self, definition):
        definition.setdefault('global', False)

        if definition['global'] and self._is_argument_positional(definition):
            raise TypeError("Positional arguments cannot be 'global': '{}'".format(definition['names'][0]))

    @staticmethod
    def _preprocess_subcommand_argument_definition(definition):
        if 'global' in definition:
            raise TypeError("'global' arguments are not available in subcommands")

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

        if self._.show_warnings and kwargs['allow_abbrev']:
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

        if self._.has_positional_arguments:
            self._log_warning_parser_has_positional_arguments_and_subcommands()

    # ------ CLI argument parsing methods ------
    def _add_subcommands(self, parser, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            name = definition.pop('name')
            subcommand = Parser(
                definition,
                show_warnings=self._.show_warnings,
                _subcommand=True,
            )

            # Create ArgumentParser instance and initialize
            parser.set_subparsers(**self.subparsers_kwargs)
            subparser = parser.add_parser(name, **subcommand.argument_parser_kwargs)
            subparser.set_defaults(**subcommand.default_kwargs)

            arguments = subcommand._get_arguments()
            arguments = subcommand._pop_elements_from_dicts(arguments, *self._custom_arg_params)
            argument_groups = self._group_arguments(arguments)
            subparser.add_arguments(*argument_groups)

            subcommand._add_subcommands(subparser, *subcommand.subcommand_definitions)

    def _parse_cli_arguments(self, argv):
        argument_parser_kwargs = self.argument_parser_kwargs.copy()
        argument_parser_kwargs['argument_default'] = sargeparse.unset

        # Create ArgumentParser instance and initialize
        ap = ArgumentParser(**argument_parser_kwargs)
        parser = _ArgumentParserHelper(ap)
        parser.set_defaults(**self.default_kwargs)

        # Add global arguments first
        global_arguments = self._get_arguments(**{'global': True})
        global_arguments = self._pop_elements_from_dicts(global_arguments, *self._custom_arg_params)
        global_argument_groups = self._group_arguments(global_arguments)
        parser.add_arguments(*global_argument_groups)

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
        arguments = self._get_arguments(**{'global': False})
        arguments = self._pop_elements_from_dicts(arguments, *self._custom_arg_params)
        argument_groups = self._group_arguments(arguments)
        parser.add_arguments(*argument_groups)

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
        self._.arguments['cli'].clear()
        self._.arguments['cli'].update(parsed_args.__dict__)

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
        for k, v in list(self._.arguments['cli'].items()):
            if v == sargeparse.unset:
                self._.arguments['cli'].pop(k)

                if self.argument_parser_kwargs['argument_default'] == sargeparse.suppress:
                    continue

                self._.arguments['arg_default'][k] = self.argument_parser_kwargs['argument_default']

    # ------ Additional argument sources' methods ------
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
            dest = self._make_dest_from_argument_names(argument_definition['names'])

            if 'envvar' in argument_definition:
                envvar = os.environ.get(argument_definition['envvar'], sargeparse.unset)
                if envvar != sargeparse.unset:
                    self._.arguments['environment'][dest] = envvar
                    envvar = argument_definition.get('type', self._same)(envvar)
                else:
                    self._.arguments['arg_default'][dest] = self.argument_parser_kwargs['argument_default']

            if 'default' in argument_definition:
                default = argument_definition['default']
                self._.arguments['defaults'][dest] = default

        for subcommand_definition in subcommand_definitions:
            self._parse_envvars_and_defaults(subcommand_definition)

    def _parse_config(self, config, definition=None):
        argument_definitions, subcommand_definitions = self._get_argument_and_subcommand_definitions(definition)

        for argument_definition in argument_definitions:
            dest = self._make_dest_from_argument_names(argument_definition['names'])

            if 'config_path' in argument_definition:
                config_value = config.get_path(argument_definition['config_path'], sargeparse.unset)
                if config_value != sargeparse.unset:
                    config_value = argument_definition.get('type', self._same)(config_value)
                    self._.arguments['configuration'][dest] = config_value
                else:
                    self._.arguments['arg_default'][dest] = self.argument_parser_kwargs['argument_default']

        for subcommand_definition in subcommand_definitions:
            self._parse_config(config, subcommand_definition)

    # ------ Logging helper methods ------
    def _log_warning_parser_has_positional_arguments_and_subcommands(self):
        if self._.show_warnings:
            LOG.warning("Having subcommands and positional arguments simultaneously is probably a bad idea")

    def _log_warning_if_missing(self, dictionary, where, *keys):
        if self._.show_warnings:
            msg = "Missing '%s' in %s. Please add something helpful, or set it to None to hide this warning"
            filtered_keys = [k for k in keys if k not in dictionary]

            for k in filtered_keys:
                LOG.warning(msg, k, where)
                dictionary[k] = 'WARNING: MISSING {} MESSAGE'.format(k.upper())

    def _log_warning_if_elements_are_different_from_none(self, dictionary, *keys):
        if self._.show_warnings:
            msg = "The default value of '%s' is probably better than: '%s'"
            filtered_dict = {k: v for k, v in dictionary.items() if k in keys and v is not None}

            for k, v in filtered_dict.items():
                LOG.warning(msg, k, v)

    # ------ Argument methods ------
    def _make_dest_from_argument_names(self, names):
        '''Get the 'dest' parameter based on the argument names'''

        dest = None

        for name in names:
            if name[0] in self._.prefix_chars and not dest:
                dest = name[1:]

            if name[0] not in self._.prefix_chars:
                dest = name
                break

            if name[0] in self._.prefix_chars and name[0] == name[1]:
                dest = name[2:]
                break

        return dest.replace('-', '_')

    def _is_argument_positional(self, definition):
        '''Return whether or not an argument is 'positional', being 'optional' the alternative'''

        return definition['names'][0][0] not in self._.prefix_chars

    def _get_arguments(self, **schema):
        '''Return arguments that match a schema (see _check_dict_elements)'''

        for argument in self.argument_definitions:
            if self._check_dict_elements(argument, **schema):
                yield argument

    def _group_arguments(self, definition_list):
        arguments = []
        mutexes = {}
        groups = {}

        # Make groups / mutex_groups from plain argument definition list
        for definition in definition_list:
            definition = definition.copy()
            target = arguments

            # Add group to 'arguments' if not there already and point target to it
            group = definition.pop('group', None)
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
            mutex = definition.pop('mutex', None)
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
            target.append(definition)

        # Set 'required' to False in mutexes when all of its arguments have 'required': False
        for mutex in mutexes.values():
            for argument in mutex['arguments']:
                if argument.get('required') is not False:
                    break
            else:
                mutex['required'] = False

        yield from arguments

    # ------ Other helper methods ------
    @staticmethod
    def _same(arg):
        return arg

    @staticmethod
    def _check_dict_elements(dictionary, **schema):
        '''Return True if the dict satisfies the schema'''

        for k, v in schema.items():
            if k in dictionary and dictionary[k] == v:
                continue
            else:
                return False

        return True

    @staticmethod
    def _pop_elements_from_dicts(dicts, *key_list):
        '''Return a copy of a dict without the elements from key_list'''

        for dictionary in dicts:
            dictionary = dictionary.copy()

            for key in key_list:
                dictionary.pop(key, None)

            yield dictionary


class _ArgumentParserHelper:
    def __init__(self, parser):
        self.parser = parser

    def add_arguments(self, *definition_list):
        for definition in definition_list:
            definition = definition.copy()

            argument_type = definition.pop('_type', None)
            if argument_type == 'group':
                self._add_group(definition, self.parser)
            elif argument_type == 'mutex':
                self._add_mutex(definition, self.parser)
            else:
                self._add_argument(definition, self.parser)

    def _add_group(self, definition, dest):
        arguments = definition.pop('arguments')
        group = dest.add_argument_group(**definition)

        for argument in arguments:
            argument_type = argument.pop('_type', None)

            if argument_type == 'mutex':
                self._add_mutex(argument, group)
            else:
                self._add_argument(argument, group)

    def _add_mutex(self, definition, dest):
        arguments = definition.pop('arguments')
        mutex = dest.add_mutually_exclusive_group(**definition)

        for argument in arguments:
            self._add_argument(argument, mutex)

    @staticmethod
    def _add_argument(definition, dest):
        names = definition.pop('names')
        dest.add_argument(*names, **definition)

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

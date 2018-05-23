import sys
import logging

import sargeparse.consts

from sargeparse.custom import ArgumentParser, HelpFormatter

LOG = logging.getLogger(__name__)


class Parser():
    def __init__(self, definition, **kwargs):
        self._show_warnings = kwargs.pop('show_warnings', True)
        self._subcommand = kwargs.pop('_subcommand', False)
        self._ap_argument_parser = None
        self._ap_subparsers = None
        self._has_positional_arguments = False

        # sargeparse wrappers
        self._prefix_chars = definition.get('prefix_chars', '-')
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

            self._init_parser(ArgumentParser(**self.argument_parser_kwargs))
            self.set_defaults(**self.default_kwargs)

    ################################################################################################
    # User methods
    def add_arguments(self, *definition_list):
        for definition in definition_list:
            self._preprocess_argument_definition(definition)
            self.argument_definitions.append(definition)

    def add_subcommands(self, *definition_list):
        for definition in definition_list:
            self._preprocess_base_ap_kwargs(definition)
            self._preprocess_subcommand_ap_kwargs(definition)

            self.subcommand_definitions.append(definition)

    def config_subparsers(self, **kwargs):
        self._log_warning_if_elements_are_different_from_none(kwargs, 'prog', 'help')

        kwargs.setdefault('title', 'subcommands')
        kwargs.setdefault('metavar', 'SUBCOMMAND')
        kwargs.setdefault('help', None)

        self.subparsers_kwargs = kwargs

    def set_defaults(self, **kwargs):
        self.default_kwargs = kwargs
        self._ap_set_defaults(**kwargs)

    def parse(self, argv=None):
        argv = sys.argv[1:] if not argv else argv

        # Add shared arguments first
        shared_arguments = self._get_arguments_pop_properties(shared=True)
        self._ap_add_arguments(*shared_arguments)

        # Replace help subcommand by --help at the end, makes it possible to use:
        # command help, command help subcommand, command help subcommand subsubcommand...
        if self.subcommand_definitions and self.help_subcommand and argv and argv[0] == 'help':
            argv.pop(0)
            argv.append('--help')

        # Parse shared options first so they can be placed anywhere, unless the --help/-h flag is set
        parsed_args, rest = None, argv
        if '-h' not in rest and '--help' not in rest:
            parsed_args, rest = self._ap_parse_known_args(rest)

        # Add the rest of arguments
        arguments = self._get_arguments_pop_properties(shared=False)
        self._ap_add_arguments(*arguments)

        # Add subcommands
        if self.subcommand_definitions and self.help_subcommand:
            self._add_help_subcommand_definition()
        self._add_subcommands(*self.subcommand_definitions)

        # TODO
        # for command in commands.values():
        #    add_subcommands_to_description(command)

        # Finish parsing args
        parsed_args = self._ap_parse_args(rest, parsed_args)
        return parsed_args.__dict__

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
    def _get_parser(self):
        '''ArgumentParser object getter, because for subcommands it's initialized by its parent object'''

        return self._ap_argument_parser

    def _init_parser(self, parser):
        '''ArgumentParser object setter, because for subcommands it's initialized by its parent object'''

        self._ap_argument_parser = parser

    def _add_subcommands(self, *definition_list):
        for definition in definition_list:
            name = definition.pop('name')
            subcommand = Parser(
                definition,
                show_warnings=self._show_warnings,
                _subcommand=True,
            )
            kwargs = subcommand.argument_parser_kwargs

            subparser = self._ap_add_parser(name, **kwargs)

            subcommand._init_parser(subparser)
            subcommand.set_defaults(**subcommand.default_kwargs)

            arguments = subcommand._get_arguments_pop_properties()
            subcommand._ap_add_arguments(*arguments)

            subcommand._add_subcommands(*subcommand.subcommand_definitions)

    @staticmethod
    def _log_warning_parser_has_positional_arguments_and_subcommands():
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

    def _get_arguments_pop_properties(self, **schema):
        '''Return a copy of arguments that match a schema, while removing their correspondent keys'''

        for argument in self._get_arguments(**schema):
            argument_copy = argument.copy()

            for k in schema:
                argument_copy.pop(k, None)

            yield argument_copy

    def _add_help_subcommand_definition(self):
        self.add_subcommands({
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
        })

    ################################################################################################
    # argparse wrappers
    def _ap_add_arguments(self, *definition_list):
        for definition in definition_list:
            names = definition.pop('names')
            self._get_parser().add_argument(*names, **definition)

    def _ap_add_subparsers(self):
        if not self._ap_subparsers:
            self._ap_subparsers = self._get_parser().add_subparsers(**self.subparsers_kwargs)

    def _ap_add_parser(self, name, **kwargs):
        self._ap_add_subparsers()
        return self._ap_subparsers.add_parser(name, **kwargs)

    def _ap_set_defaults(self, **kwargs):
        self._get_parser().set_defaults(**kwargs)

    def _ap_parse_args(self, *args, **kwargs):
        return self._get_parser().parse_args(*args, **kwargs)

    def _ap_parse_known_args(self, *args, **kwargs):
        return self._get_parser().parse_known_args(*args, **kwargs)

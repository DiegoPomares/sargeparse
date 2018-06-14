import os
import re
import logging
import collections

import sargeparse.consts

from sargeparse.context_manager import check_kwargs

LOG = logging.getLogger(__name__)


class Argument:
    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        with check_kwargs(kwargs):
            self._show_warnings = kwargs.pop('show_warnings')
            self._prefix_chars = kwargs.pop('prefix_chars')
            main_command = kwargs.pop('main_command')

        self.custom_parameters = {
            'show_default': definition.pop('show_default', False),
            'group': definition.pop('group', None),
            'mutex_group': definition.pop('mutex_group', None),
            'global': definition.pop('global', False),
            'default': definition.pop('default', sargeparse.unset),
            'envvar': definition.pop('envvar', sargeparse.unset),
            'config_path': definition.pop('config_path', sargeparse.unset),
        }

        self.names = None
        self.dest = None
        self.group = self.custom_parameters['group']
        self.mutex_group = self.custom_parameters['mutex_group']
        self.add_argument_kwargs = definition

        self._process_add_argument_kwargs(main_command=main_command)
        self._process_custom_parameters(main_command=main_command)

    def get_value_from_envvar(self, *, default=None):
        """Return value as read from the environment variable, and apply its type"""

        if self.custom_parameters['envvar'] == sargeparse.unset:
            return default

        envvar = self.custom_parameters['envvar']
        if envvar not in os.environ:
            return default

        value = os.environ[envvar]
        return self._apply_type(value)

    def get_default_value(self, *, default=None, apply_type=False):
        """Return default value from add_argument() kwargs"""

        if self.custom_parameters['default'] == sargeparse.unset:
            return default

        value = self.custom_parameters['default']
        if not apply_type:
            return value

        return self._apply_type(value)

    def get_value_from_config(self, config, *, default=None):
        """Return value from dict, and apply its type"""

        if self.custom_parameters['config_path'] == sargeparse.unset:
            return default

        config_path = self.custom_parameters['config_path']
        try:
            value = self._get_value_from_path(config, config_path)
        except KeyError:
            return default

        return self._apply_type(value)

    def is_positional(self):
        """Return whether or not an argument is 'positional', being 'optional' the alternative"""

        return self.names[0][0] not in self._prefix_chars

    def validate_schema(self, schema):
        """Return True if the argument satisfies the schema"""

        for k, v in schema.items():
            definition = collections.ChainMap(self.add_argument_kwargs, self.custom_parameters)
            if k in definition and definition[k] == v:
                continue
            else:
                return False

        return True

    def _apply_type(self, value):
        fn = self.add_argument_kwargs.get('type', self._same)

        if isinstance(value, list):
            return [fn(v) for v in value]

        return fn(value)

    def _process_add_argument_kwargs(self, main_command):
        self._process_common_add_argument_kwargs()

        if main_command:
            self._process_add_argument_kwargs_for_main_command()
        else:
            self._process_add_argument_kwargs_for_subcommand()

    def _process_common_add_argument_kwargs(self):
        self.names = self.add_argument_kwargs.pop('names', None)
        if not self.names:
            raise TypeError("Argument 'names' missing or invalid")

        self.dest = self._make_dest_from_argument_names()

        if 'help' not in self.add_argument_kwargs and self._show_warnings:
            msg = "Missing 'help' in %s. Please add something helpful, or set it to None to hide this warning"
            LOG.warning(msg, self.dest)
            self.add_argument_kwargs['help'] = "WARNING: MISSING HELP MESSAGE"
        else:
            self.add_argument_kwargs['help'] = self.add_argument_kwargs['help'] or ''

        self._add_default_value_to_help()

        if self.is_positional():
            # argparse will raise an exception if the argument is positional and 'dest' is set
            if 'dest' in self.add_argument_kwargs:
                msg = "Positional arguments cannot have a 'dest', remove it from the definition: '{}'".format(
                    self.add_argument_kwargs['dest']
                )
                raise TypeError(msg)

        else:  # argument is optional
            self.add_argument_kwargs.setdefault('dest', self.dest)

    def _process_add_argument_kwargs_for_main_command(self):
        if self.custom_parameters['global'] and self.is_positional():
            raise TypeError("Positional arguments cannot be 'global': '{}'".format(self.names[0]))

    def _process_add_argument_kwargs_for_subcommand(self):
        if self.custom_parameters['global']:
            raise TypeError("Subcommands' arguments cannot be 'global'")

    def _process_custom_parameters(self, main_command):
        self._process_common_custom_parameters()

        if main_command:
            self._process_custom_parameters_for_main_command()
        else:
            self._process_custom_parameters_for_subcommand()

    def _process_common_custom_parameters(self):
        # Override default group names
        if not self.group:
            if self.custom_parameters.get('global'):
                self.group = 'general arguments'

            elif self.add_argument_kwargs.get('required'):
                self.group = 'required arguments'

            else:
                self.group = 'optional arguments'

        # Validate 'config_path'
        config_path = self.custom_parameters['config_path']
        if config_path != sargeparse.unset:
            if isinstance(config_path, str):
                self.custom_parameters['config_path'] = re.split(r'(?<!\\)/', config_path)

            elif not (
                    config_path and
                    isinstance(config_path, list) and
                    all((isinstance(v, str) for v in config_path))
            ):
                raise TypeError("Paths in 'config_path' can only be <str> or <list of str>")

    def _process_custom_parameters_for_main_command(self):
        pass

    def _process_custom_parameters_for_subcommand(self):
        pass

    def _make_dest_from_argument_names(self):
        """Get the 'dest' parameter based on the argument names"""

        dest = None

        for name in self.names:
            if name[0] in self._prefix_chars and not dest:
                dest = name[1:]

            if name[0] not in self._prefix_chars:
                dest = name
                break

            if name[0] in self._prefix_chars and name[0] == name[1]:
                dest = name[2:]
                break

        return dest.replace('-', '_')

    def _add_default_value_to_help(self):
        if all((
                self.custom_parameters['show_default'],
                self.add_argument_kwargs['help'] != sargeparse.suppress,
                self.get_default_value(default=sargeparse.unset) != sargeparse.unset,
        )):
            if self.add_argument_kwargs['help']:
                self.add_argument_kwargs['help'] += " "

            self.add_argument_kwargs['help'] += "(default: {})".format(self.get_default_value())

    def _get_value_from_path(self, dictionary, path):
        """Return the value for path, where path represent a list of keys in nested dicts separated by '/'"""

        key = path[0]

        if len(path) == 1:
            return dictionary[key]

        return self._get_value_from_path(dictionary[key], path[1:])

    @staticmethod
    def _same(arg):
        """This is used as the default function for 'type' parameter"""
        return arg

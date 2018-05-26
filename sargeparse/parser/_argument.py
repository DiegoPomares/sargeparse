import os
import re
import logging

from sargeparse.parser.context_manager import CheckKwargs

LOG = logging.getLogger(__name__)


class Argument:
    _custom_parameters = ['default', 'global', 'envvar', 'config_path']

    def __init__(self, definition, **kwargs):
        definition = definition.copy()

        with CheckKwargs(kwargs) as d:
            subcommand = d.pop('subcommand')
            self._show_warnings = d.pop('show_warnings')
            self._prefix_chars = d.pop('prefix_chars')

        self.names = None
        self.dest = None
        self._definition = definition

        self._process_definition(for_subcommand=subcommand)

    def is_positional(self):
        """Return whether or not an argument is 'positional', being 'optional' the alternative"""

        return self.names[0][0] not in self._prefix_chars

    def get_definition(self):
        """Return the argument definition"""

        return self._definition.copy()

    def validate_schema(self, schema):
        """Return True if the argument satisfies the schema"""

        for k, v in schema.items():
            if k in self._definition and self._definition[k] == v:
                continue
            else:
                return False

        return True

    def get_value_from_envvar(self, *, default=None):
        """Return value as read from the environment variable, and apply its type"""

        if 'envvar' not in self._definition:
            return default

        envvar = self._definition['envvar']
        if envvar not in os.environ:
            return default

        value = os.environ[envvar]
        return self._definition.get('type', self._same)(value)

    def get_default_value(self, *, default=None):
        """Return default value from the argument definition"""

        if 'default' not in self._definition:
            return default

        return self._definition['default']

    def get_value_from_config(self, config, *, default=None):
        """Return value from dict, and apply its type"""

        if 'config_path' not in self._definition:
            return default

        config_path = self._definition['config_path']
        try:
            value = self._get_value_from_path(config, config_path)
        except KeyError:
            return default

        return self._definition.get('type', self._same)(value)

    def get_definition_without_custom_parameters(self):
        """Return the argument definition removing selected keys"""

        definition = self._definition.copy()
        for key in self._custom_parameters:
            definition.pop(key, None)

        return definition

    def _process_definition(self, for_subcommand):
        self._process_common_definition()

        if for_subcommand:
            self._process_definition_for_subcommand()
        else:
            self._process_definition_for_parser()

    def _process_common_definition(self):
        self.names = self._definition.pop('names', None)
        if not self.names:
            raise TypeError("Argument 'names' missing or invalid")

        self.dest = self._make_dest_from_argument_names(self.names)

        if not self._definition.get('help') and self._show_warnings:
            msg = "Missing 'help' in %s. Please add something helpful, or set it to None to hide this warning"
            LOG.warning(msg, self.dest)
            self._definition['help'] = "WARNING: MISSING HELP MESSAGE"

        if self.is_positional():
            # argparse will raise an exception if the argument is positional and 'dest' is set
            if 'dest' in self._definition:
                msg = "Positional arguments cannot have a 'dest', remove it from the definition: '{}'".format(
                    self._definition['dest']
                )
                raise TypeError(msg)

        else:  # argument is optional
            self._definition.setdefault('dest', self.dest)

    def pop_parameter(self, *args):
        return self._definition.pop(*args)

    def _process_definition_for_parser(self):
        self._definition.setdefault('global', False)

        if self._definition['global'] and self.is_positional():
            raise TypeError("Positional arguments cannot be 'global': '{}'".format(self.names[0]))

    def _process_definition_for_subcommand(self):
        if 'global' in self._definition:
            raise TypeError("'global' arguments are not available in subcommands")

    def _make_dest_from_argument_names(self, names):
        """Get the 'dest' parameter based on the argument names"""

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

    def _get_value_from_path(self, dictionary, path):
        """Return the value for path, where path represent a list of keys in nested dicts separated by '/'"""

        if isinstance(path, str):
            path = re.split(r'(?<!\\)/', path)
        elif not isinstance(path, list):
            path = [path]

        if path:
            key = path[0]
        else:
            raise RuntimeError("Invalid path config_path, it's probably better to use strings")

        if len(path) > 1:
            if key not in dictionary:
                raise KeyError("Path not found")

            return self._get_value_from_path(dictionary[key], path[1:])

        return dictionary[key]

    @staticmethod
    def _same(arg):
        return arg

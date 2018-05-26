import sys
import argparse
import textwrap
import shutil
import re
import pprint


class EZObject:
    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __repr__(self):
        return '<{}\n{}\n>'.format(type(self).__name__, pprint.pformat(self.__dict__, indent=2))


class PathDict(dict):
    def get_path(self, path, default=None):
        """Return the value for path, where path represent a list of keys in nested dicts separated by '/'"""

        if isinstance(path, str):
            path = re.split(r'(?<!\\)/', path)

        if path:
            key = path[0]
        else:
            raise RuntimeError("Invalid path")

        if len(path) > 1:
            if key not in self:
                return default

            return PathDict(self[key]).get_path(path[1:], default)

        return super().get(key, default)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: {}\n\n'.format(message))
        self.print_usage()
        sys.exit(2)


class HelpFormatter(argparse.HelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._width = self._get_terminal_width()

    @staticmethod
    def _get_terminal_width():
        width, _ = shutil.get_terminal_size()
        width = max((width, 120))
        return width

    def _fill_text(self, text, width, indent):
        return textwrap.fill(
            text,
            width,
            initial_indent=indent,
            subsequent_indent=indent,
            replace_whitespace=False,
        )

    @staticmethod
    def _subparsers_remove_header(action):
        return all((
            isinstance(action, argparse._SubParsersAction),
            action.help is None,
        ))

    def _iter_indented_subactions(self, action):
        """Fix indentation when removing subcommand metavar/help empty line"""

        indent = not self._subparsers_remove_header(action)

        try:
            get_subactions = action._get_subactions
        except AttributeError:
            pass
        else:
            if indent:
                self._indent()

            yield from get_subactions()

            if indent:
                self._dedent()

    def _format_action(self, action):
        """ Remove subcommand metavar/help empty line when both metavar/help are empty"""

        result = super()._format_action(action)

        if self._subparsers_remove_header(action):
            result = result.split('\n', maxsplit=1)[1]

        return result

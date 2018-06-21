import sys
import argparse
import textwrap
import shutil


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print('error: {}\n\n'.format(message), file=sys.stderr, end='')
        self.print_usage()
        sys.exit(2)


class HelpFormatter(argparse.HelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._width = self._get_terminal_width()

    @staticmethod
    def _get_terminal_width():
        width, height_ = shutil.get_terminal_size()
        width = max((width, 120))
        return width

    def _fill_text(self, text, width, indent):
        lines = text.splitlines()
        wrapped_lines = []

        for line in lines:
            wrapped_lines.append(textwrap.fill(
                line,
                width,
                initial_indent=indent,
                subsequent_indent=indent,
                replace_whitespace=False,
            ))

        return '\n'.join(wrapped_lines)

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

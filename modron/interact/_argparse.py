from argparse import HelpFormatter, ArgumentParser, RawTextHelpFormatter
from io import StringIO
from typing import Text, Optional, IO, NoReturn


class NoExitParserError(Exception):
    """Error when parsing fails.

    Captures the error message and what was printed to screen from the
    parser that threw the error. This allows for the screen output
    from subparsers to be easily accessed by the user, as they will
    be passed along with the exception itself."""

    def __init__(self, parser: 'NoExitParser', error_message: Text,
                 text_output: Text):
        super().__init__()
        self.parser = parser
        self.error_message = error_message
        self.text_output = text_output


class MarkdownFormatter(RawTextHelpFormatter):
    """Argparse HelpFormatter that renders the help in markdown format"""

    class _Section(HelpFormatter._Section):
        def __init__(self, formatter, parent, heading=None):
            self.formatter = formatter
            self.parent = parent
            self.heading = heading
            self.items = []

        def format_help(self):
            # format the indented section
            if self.parent is not None:
                self.formatter._indent()
            join = self.formatter._join_parts
            item_help = join([func(*args) for func, args in self.items])
            if self.parent is not None:
                self.formatter._dedent()

            # return nothing if the section was empty
            if not item_help:
                return ''

            # add the heading if the section was non-empty
            if self.heading is not None:
                current_indent = self.formatter._current_indent
                heading = f'{"#"*(current_indent+2)} {self.heading}\n\n'
            else:
                heading = ''

            # join the section-initial newline, the heading and the help
            return join(['\n', heading, item_help, '\n'])

    def _format_usage(self, usage: Text, actions,
                      groups, prefix: Optional[Text]):
        if prefix is None:
            prefix = '*usage*: '
        return super()._format_usage(usage, actions, groups, prefix)

    def _format_action(self, action):
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_header = self._format_action_invocation(action)

        # determine if this is a subaction command
        subactions = list(self._iter_indented_subactions(action))
        if len(subactions) == 0:
            # make the action part of a indented list
            parts = [f'{" " * self._current_indent}- *{action_header}*\n']

            # if there was help for the action, add lines of help text
            #  Split the help into multiple lines even though it will
            #  get dynamically re-sized by the Markdown renderer
            if action.help:
                help_text = self._expand_help(action)
                help_lines = self._split_lines(help_text, help_width)
                parts.extend(help_lines)

            # or add a newline if the description doesn't end with one
            parts.append('\n')

        else:
            # Print out the sub-options in a nice way
            assert action_header.startswith('{') and action_header.endswith('}'), 'Unexpected header format'
            parts = []

            # if there are any sub-actions, add their help as well
            for subaction in subactions:
                parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)


class NoExitParser(ArgumentParser):
    """A version of ArgumentParser that does not terminate on exit"""

    def __init__(self, *args, **kwargs):
        #  formatter_class=MarkdownFormatter,
        super().__init__(*args,  formatter_class=MarkdownFormatter, **kwargs)
        self.text_buffer = StringIO()

    def _print_message(self, message: str, file: Optional[IO[str]] = ...) -> None:
        if message:
            self.text_buffer.write(message)
            self.text_buffer.flush()

    def exit(self, status: int = ..., message: Optional[Text] = None) -> NoReturn:
        raise NoExitParserError(self, message, self.text_buffer.getvalue())

    def error(self, message: Text) -> NoReturn:
        raise NoExitParserError(self, message, self.text_buffer.getvalue())

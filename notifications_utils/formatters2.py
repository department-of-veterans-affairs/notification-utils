"""
This file implements custom behavior with Mistune, which is a Python library for processing markdown.
Advanced use cases are not well documented and require inspection of the Mistune source code.
    - https://mistune.lepture.com/en/latest/index.html
    - https://github.com/lepture/mistune/tree/main
"""

import re
from typing import Any, Match

import mistune
from mistune.block_parser import BlockParser
from mistune.core import BlockState
from mistune.list_parser import _parse_list_item, _transform_tight_list
from mistune.plugins import import_plugin
from mistune.renderers.html import HTMLRenderer
from mistune.renderers.markdown import MarkdownRenderer
from mistune.util import expand_leading_tab, expand_tab

from notifications_utils.formatters import get_action_link_image_url


# These styles are included in email_template2.jinja2, but some mail clients seem to drop them when a message
# is forwarded.  Include them inline as a workaround.
ACTION_LINK_IMG_STYLE = 'margin-right: 2mm; vertical-align: middle;'
BLOCK_QUOTE_STYLE = 'background: #F1F1F1; font-family: Helvetica, Arial, sans-serif; ' \
                    'font-size: 16px; line-height: 25px; margin: 16px 0;'

# Used for rendering plain text
COLUMN_WIDTH = 65

# These are copied and modified, as necessary, from Mistune's block_parser.py file for Notify's non-standard
# block quote markdown using ^.
_BLOCK_QUOTE_LEADING = re.compile(r'^ *(?:>|\^)', flags=re.M)
_BLOCK_QUOTE_TRIM = re.compile(r'^ ?', flags=re.M)
_LINE_BLANK_END = re.compile(r'\n[ \t]*\n$')
_STRICT_BLOCK_QUOTE = re.compile(r'( {0,3}(?:>|\^)[^\n]*(?:\n|$))+')

# Matches a Markdown-style action link: >>[text](url)
# Example: >>[Action](https://example.com)
ACTION_LINK_PATTERN = re.compile(
    r'^(?P<block_quote> {0,3}(?:>|\^)[ \t]+)?(?:>|&gt;){2}\[(?P<link_text>[^\]]+)\]\((?P<url>\S+)\)(?P<extra>.+?)?$',
    flags=re.M
)

# Block quotes can be denoted with > (standard) or ^ (Notify).  This is a modification of the regex found in
# mistune.block_parser.py.
NOTIFY_BLOCK_QUOTE_PATTERN = r'^ {0,3}(?:>|\^)(?P<quote_1>.*?)$'

# List items can be denoted with -|+|* (standard ) or • (Notify).  This is a modification of the regex found
# in mistune.list_parser.py.
NOTIFY_LIST_PATTERN = (
    r'^(?P<list_1> {0,3})'
    r'(?P<list_2>[\*\+•-]|\d{1,9}[.)])'
    r'(?P<list_3>[ \t]*|[ \t].+)$'
)


def insert_action_links(markdown: str, as_html: bool = True) -> str:
    """
    Finds an "action link," and replaces it with the desired format. This preprocessing should take place before
    any manipulation by Mistune.  The CSS class "action_link" should be defined in a Jinja2 template.  If the
    action links is in a block quote, new lines must also be in a block quote.  Text following the action link,
    if any, should break onto a new line.
    """

    if as_html:
        return ACTION_LINK_PATTERN.sub(_get_action_link_html_substitution, markdown)

    return ACTION_LINK_PATTERN.sub(_get_action_link_plain_text_substitution, markdown)


def _get_action_link_html_substitution(m: Match[str]) -> str:
    """
    Given:
        >>[text](url)

    HTML Output:
        \n\n<a href="url"><img alt="call to action img" aria-hidden="true" src="..."
        class="action_link"><b>text</b></a>\n\n
    """

    url = m.group('url')
    link_text = m.group('link_text')
    img_src = get_action_link_image_url()
    is_block_quote = m.group('block_quote') is not None

    if is_block_quote:
        # The action link is in a block quote.
        substitution = f'> <a href="{url}">' \
                       f'<img alt="call to action img" aria-hidden="true" src="{img_src}" class="action_link" ' \
                       f'style="{ACTION_LINK_IMG_STYLE}">' \
                       f'<b>{link_text}</b></a>\n>'
    else:
        substitution = f'\n\n<a href="{url}">' \
                       f'<img alt="call to action img" aria-hidden="true" src="{img_src}" class="action_link" ' \
                       f'style="{ACTION_LINK_IMG_STYLE}">' \
                       f'<b>{link_text}</b></a>\n\n'

    if m.group('extra') is not None:
        extra = m.group('extra')
        prefix = '\n> ' if is_block_quote else ''
        substitution += f'{prefix}{extra}\n'

    return substitution


def _get_action_link_plain_text_substitution(m: Match[str]) -> str:
    """
    Substitute an ordinary link for an action link.
    """

    url = m.group('url')
    link_text = m.group('link_text')
    is_block_quote = m.group('block_quote') is not None

    if is_block_quote:
        # The action link is in a block quote.
        substitution = f'> [{link_text}]({url})\n>'
    else:
        substitution = f'[{link_text}]({url})\n\n'

    if m.group('extra') is not None:
        extra = m.group('extra')
        prefix = '\n> ' if is_block_quote else ''
        substitution += f'{prefix}{extra}\n'

    return substitution


class NotifyHTMLRenderer(HTMLRenderer):
    def block_quote(self, text):
        """
        Add styling for block quotes.
        """

        value = super().block_quote(text)
        return value[:11] + f' class="notify" style="{BLOCK_QUOTE_STYLE}"' + value[11:]

    def image(self, alt, url, title=None):
        """
        VA e-mail messages generally contain only 1 header image that is not managed by clients.
        There is also an image associated with "action links", but action links are handled
        in preprocessing.  (See insert_action_link above.)
        """

        return ''

    def paragraph(self, text):
        """
        Remove empty paragraphs.
        """

        value = super().paragraph(text)

        if value == '<p></p>\n':
            # This is the case when all child elements, such as tables and images, are deleted.
            return ''

        return value

    def table(self, text):
        """
        Delete tables.
        """

        return ''


class NotifyMarkdownRenderer(MarkdownRenderer):
    def block_quote(self, token, state):
        value = super().block_quote(token, state)

        # The superclass method prepends each line with "> ".  Remove that prefix.
        return '\n\n' + re.sub(r'^> ', '', value, flags=re.M)

    def heading(self, token, state):
        value = super().heading(token, state)
        indentation = 3 if token['attrs']['level'] == 1 else 2
        return ('\n' * indentation) + value.strip('#\n ') + '\n' + ('-' * COLUMN_WIDTH) + '\n'

    def image(self, token, state):
        """
        Delete images.  VA e-mail messages contain only 1 image that is not managed by clients.
        """

        return ''

    def link(self, token, state):
        """
        Input:
            [text](url)
        Output:
            text: url
        """

        return self.render_children(token, state) + ': ' + token['attrs']['url']

    def list(self, token, state):
        """
        Use the bullet character as the actual bullet output for all input (asterisks, pluses, and minues)
        when the list is unordered.
        """

        if not token['attrs']['ordered']:
            token['bullet'] = '•'

        return super().list(token, state)

    def strikethrough(self, token, state):
        """
        https://mistune.lepture.com/en/latest/renderers.html#with-plugins
        """

        return '\n\n' + self.render_children(token, state)

    def table(self, token, state):
        """
        Delete tables.
        """

        return ''

    def thematic_break(self, token, state):
        """
        Thematic breaks were known as horizontal rules (hrule) in earlier versions of Mistune.
        """

        return '=' * COLUMN_WIDTH + '\n'


class NotifyBlockParser(BlockParser):
    """
    Parse standard Github markdown with some Notify-specific additions.

    https://github.com/lepture/mistune/blob/main/src/mistune/block_parser.py
    """

    def __init__(self) -> None:
        self.SPECIFICATION['block_quote'] = NOTIFY_BLOCK_QUOTE_PATTERN
        self.SPECIFICATION['list'] = NOTIFY_LIST_PATTERN
        super(NotifyBlockParser, self).__init__()

    def extract_block_quote(self, m: Match[str], state: BlockState) -> tuple[str, int]:  # noqa: C901
        """
        Extract text and the cursor end position of a block quote.

        This method mostly is copied from the parent class, which uses module level
        regular expressions.  This method uses modified regular expressions correctly
        to extract block quotes using the non-standard ^ denotation.
        """

        # Cleanup to detect if this is a code block.
        text = m.group('quote_1') + '\n'
        text = expand_leading_tab(text, 3)
        text = _BLOCK_QUOTE_TRIM.sub('', text)

        sc = self.compile_sc(["blank_line", "indent_code", "fenced_code"])
        require_marker = bool(sc.match(text))
        state.cursor = m.end() + 1
        end_pos: int | None = None

        if require_marker:
            m2 = _STRICT_BLOCK_QUOTE.match(state.src, state.cursor)
            if m2:
                quote = m2.group(0)
                quote = _BLOCK_QUOTE_LEADING.sub("", quote)
                quote = expand_leading_tab(quote, 3)
                quote = _BLOCK_QUOTE_TRIM.sub("", quote)
                text += quote
                state.cursor = m2.end()
        else:
            prev_blank_line = False
            break_sc = self.compile_sc(
                [
                    "blank_line",
                    "thematic_break",
                    "fenced_code",
                    "list",
                    "block_html",
                ]
            )
            while state.cursor < state.cursor_max:
                m3 = _STRICT_BLOCK_QUOTE.match(state.src, state.cursor)
                if m3:
                    quote = m3.group(0)
                    quote = _BLOCK_QUOTE_LEADING.sub("", quote)
                    quote = expand_leading_tab(quote, 3)
                    quote = _BLOCK_QUOTE_TRIM.sub("", quote)
                    text += quote
                    state.cursor = m3.end()
                    if not quote.strip():
                        prev_blank_line = True
                    else:
                        prev_blank_line = bool(_LINE_BLANK_END.search(quote))
                    continue

                if prev_blank_line:
                    # CommonMark Example 249
                    # Because of laziness, a blank line is needed between a block quote and a following paragraph.
                    break

                m4 = break_sc.match(state.src, state.cursor)
                if m4:
                    end_pos = self.parse_method(m4, state)
                    if end_pos:
                        break

                # lazy continuation line
                pos = state.find_line_end()
                line = state.get_text(pos)
                line = expand_leading_tab(line, 3)
                text += line
                state.cursor = pos

        # According to CommonMark Example 6, the second tab should be treated as 4 spaces.
        return expand_tab(text), end_pos

    def parse_list(self, m: Match[str], state: BlockState) -> int:  # noqa: C901
        """
        Parse tokens for ordered and unordered list.

        This method mostly is copied from mistune.list_parser.py::parse_list.  It contains minor
        modifications correctly to handle Notify's non-standard use of • for unordered lists.

        https://github.com/lepture/mistune/blob/main/src/mistune/list_parser.py
        """

        text = m.group("list_3")
        if not text.strip():
            # An empty list item cannot interrupt a paragraph.
            end_pos = state.append_paragraph()
            if end_pos:
                return end_pos

        marker = m.group("list_2")
        ordered = len(marker) > 1
        depth = state.depth()
        token: dict[str, Any] = {
            "type": "list",
            "children": [],
            "tight": True,
            "bullet": marker[-1],
            "attrs": {
                "depth": depth,
                "ordered": ordered,
            },
        }

        if ordered:
            start = int(marker[:-1])
            if start != 1:
                # Allow only lists starting with 1 to interrupt paragraphs.
                end_pos = state.append_paragraph()
                if end_pos:
                    return end_pos
                token["attrs"]["start"] = start

        state.cursor = m.end() + 1
        groups = (m.group("list_1"), marker, text)

        if depth >= self.max_nested_level - 1:
            rules = list(self.list_rules)
            rules.remove("list")
        else:
            rules = self.list_rules

        bullet = _get_list_bullet(marker[-1])
        while groups:
            groups = _parse_list_item(self, bullet, groups, token, state, rules)

        end_pos = token.pop("_end_pos", None)
        _transform_tight_list(token)
        if end_pos:
            index = token.pop("_tok_index")
            state.tokens.insert(index, token)
            return end_pos

        state.append_token(token)
        return state.cursor


def _get_list_bullet(c: str) -> str:
    """
    Copied from mistune.list_parser.py::parse_list, and modified to support the literal bullet.
    """

    if c == '.':
        bullet = r'\d{0,9}\.'
    elif c == ")":
        bullet = r'\d{0,9}\)'
    elif c == '*':
        bullet = r'\*'
    elif c == '+':
        bullet = r'\+'
    elif c == '•':
        # Accommodate Notify's non-standard markdown.
        bullet = r'•'
    else:
        bullet = '-'
    return bullet


# Use this markdown for HTML.
notify_html_markdown = mistune.Markdown(
    renderer=NotifyHTMLRenderer(escape=False),
    block=NotifyBlockParser(),
    inline=mistune.InlineParser(hard_wrap=True),
    plugins=[import_plugin(plugin) for plugin in ('strikethrough', 'table', 'url')],
)

# Use this markdown for plain text.
notify_markdown = mistune.Markdown(
    renderer=NotifyMarkdownRenderer(),
    block=NotifyBlockParser(),
    plugins=[import_plugin(plugin) for plugin in ('strikethrough', 'table')],
)

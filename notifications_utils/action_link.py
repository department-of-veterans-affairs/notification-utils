"""
A Mistune plugin to parse "action links" in markdown.  An action link is specified like this:
    >>[action](https://example.com/foo?a=b)
"""

from re import Match

from mistune.block_parser import BlockParser
from mistune.core import BlockState
from mistune.markdown import Markdown
from mistune.util import escape_url


ACTION_LINK_PATTERN = r'''>>\[(?P<text>[\w ]+)\]\((?P<url>\S+)\)'''
# ACTION_LINK_PATTERN = r'''\[action'''


def parse_action_link(block: BlockParser, m: Match[str], state: BlockState) -> int:
    # print("PARSE ACTION LINK", m)  # TODO - delete
    text = m.group('text')
    url = m.group('url')
    state.append_token({
        'type': 'action_link',
        'attrs': {
            'text': text,
            'url': escape_url(url),
        },
    })
    return m.end()


def action_link(md: Markdown):
    md.block.register("block_action_link", ACTION_LINK_PATTERN, parse_action_link, before='block_text')

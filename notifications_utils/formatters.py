import os
import re
import string

import bleach
import mistune
import smartypants
from markupsafe import Markup
from mistune.renderers.html import HTMLRenderer
from mistune.renderers.markdown import MarkdownRenderer
from . import email_with_smart_quotes_regex
from notifications_utils.sanitise_text import SanitiseSMS

PARAGRAPH_STYLE = 'Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;'
LINK_STYLE = 'word-wrap: break-word; color: #004795;'

OBSCURE_WHITESPACE = (
    '\u180E'  # Mongolian vowel separator
    '\u200B'  # zero width space
    '\u200C'  # zero width non-joiner
    '\u200D'  # zero width joiner
    '\u2060'  # word joiner
    '\uFEFF'  # zero width non-breaking space
)


govuk_not_a_link = re.compile(
    r'(?<!\.|\/)(GOV)\.(UK)(?!\/|\?)',
    re.IGNORECASE
)

dvla_markup_tags = re.compile(
    str('|'.join('<{}>'.format(tag) for tag in {
        'cr', 'h1', 'h2', 'p', 'normal', 'op', 'np', 'bul', 'tab'
    })),
    re.IGNORECASE
)

smartypants.tags_to_skip = smartypants.tags_to_skip + ['a']

whitespace_before_punctuation = re.compile(r'[ \t]+([,|\.])')

hyphens_surrounded_by_spaces = re.compile(r'\s+[-|–|—]{1,3}\s+')

multiple_newlines = re.compile(r'((\n)\2{2,})')

MAGIC_SEQUENCE = "🇬🇧🐦✉️"
magic_sequence_regex = re.compile(MAGIC_SEQUENCE)

# The Mistune URL regex only matches URLs at the start of a string,
# using `^`, so we slice that off and recompile
url = re.compile(r'''(https?:\/\/[^\s<]+[^<.,:"')\]\s])''')


def unlink_govuk_escaped(message):
    return re.sub(
        govuk_not_a_link,
        r'\1' + '.\u200B' + r'\2',  # Unicode zero-width space
        str(message)
    )


def nl2br(value):
    return re.sub(r'\n|\r', '<br>', value.strip())


def nl2li(value):
    return '<ul><li>{}</li></ul>'.format('</li><li>'.join(
        value.strip().split('\n')
    ))


def add_prefix(body, prefix=None):
    if prefix:
        return f'{prefix.strip()}: {body}'
    return body


def autolink_sms(body):
    return url.sub(
        lambda match: '<a style="{}" href="{}">{}</a>'.format(
            LINK_STYLE,
            match.group(1), match.group(1),
        ),
        body,
    )


def prepend_subject(body, subject):
    return '# {}\n\n{}'.format(subject, body)


def remove_empty_lines(lines):
    return '\n'.join(filter(None, str(lines).split('\n')))


def sms_encode(content):
    return SanitiseSMS.encode(str(content))


def strip_html(value):
    return bleach.clean(value, tags=[], strip=True)


def escape_html(value):
    if not value:
        return value
    value = str(value).replace('<', '&lt;')
    return bleach.clean(value, tags=[], strip=False)


def strip_dvla_markup(value):
    return re.sub(dvla_markup_tags, '', value)


def url_encode_full_stops(value):
    return value.replace('.', '%2E')


def unescaped_formatted_list(
    items,
    conjunction='and',
    before_each='‘',
    after_each='’',
    separator=', ',
    prefix='',
    prefix_plural=''
):
    if prefix:
        prefix += ' '
    if prefix_plural:
        prefix_plural += ' '

    if len(items) == 1:
        return '{prefix}{before_each}{items[0]}{after_each}'.format(**locals())
    elif items:
        formatted_items = ['{}{}{}'.format(before_each, item, after_each) for item in items]

        first_items = separator.join(formatted_items[:-1])
        last_item = formatted_items[-1]
        return (
            '{prefix_plural}{first_items} {conjunction} {last_item}'
        ).format(**locals())


def formatted_list(
    items,
    conjunction='and',
    before_each='‘',
    after_each='’',
    separator=', ',
    prefix='',
    prefix_plural=''
):
    return Markup(
        unescaped_formatted_list(
            [escape_html(x) for x in items],
            conjunction,
            before_each,
            after_each,
            separator,
            prefix,
            prefix_plural
        )
    )


def fix_extra_newlines_in_dvla_lists(dvla_markup):
    return dvla_markup.replace(
        '<cr><cr><cr><op>',
        '<cr><op>',
    )


def strip_pipes(value):
    return value.replace('|', '')


def remove_whitespace_before_punctuation(value):
    return re.sub(
        whitespace_before_punctuation,
        lambda match: match.group(1),
        str(value)
    )


def make_quotes_smart(value):
    return smartypants.smartypants(
        value,
        smartypants.Attr.q | smartypants.Attr.u
    )


def replace_hyphens_with_en_dashes(value):
    return re.sub(
        hyphens_surrounded_by_spaces,
        (
            ' '       # space
            '\u2013'  # en dash
            ' '       # space
        ),
        value,
    )


def replace_hyphens_with_non_breaking_hyphens(value):
    return value.replace(
        '-',
        '\u2011',  # non-breaking hyphen
    )


def normalise_newlines(value):
    return '\n'.join(value.splitlines())


def strip_leading_whitespace(value):
    return value.lstrip()


def add_trailing_newline(value):
    return f'{value}\n'


def tweak_dvla_list_markup(value):
    return value.replace('<cr><cr><np>', '<cr><np>').replace('<p><cr><p><cr>', '<p><cr>')


def remove_smart_quotes_from_email_addresses(value):

    def remove_smart_quotes(match):
        value = match.group(0)
        for character in '‘’':
            value = value.replace(character, "'")
        return value

    return email_with_smart_quotes_regex.sub(
        remove_smart_quotes,
        value,
    )


def strip_whitespace(value, extra_characters=''):
    if value is not None and hasattr(value, 'strip'):
        return value.strip(string.whitespace + OBSCURE_WHITESPACE + extra_characters)
    return value


def strip_and_remove_obscure_whitespace(value):
    for character in OBSCURE_WHITESPACE:
        value = value.replace(character, '')

    return value.strip(string.whitespace)


def strip_unsupported_characters(value):
    return value.replace('\u2028', '')


def normalise_whitespace(value):
    # leading and trailing whitespace removed, all inner whitespace becomes a single space
    return ' '.join(strip_and_remove_obscure_whitespace(value).split())


def get_action_links(html: str) -> list[str]:
    """Get the action links from the html email body and return them as a list. (insert_action_link helper)"""
    # set regex to find action link in html, should look like this:
    # &gt;&gt;<a ...>link_text</a>
    action_link_regex = re.compile(
        r'(>|(&gt;)){2}(<a style=".+?" href=".+?"( title=".+?")? target="_blank">)(.*?</a>)'
    )

    return re.findall(action_link_regex, html)


def get_action_link_image_url() -> str:
    """Get action link image url for the current environment. (insert_action_link helper)"""
    env_map = {
        'production': 'prod',
        'staging': 'staging',
        'performance': 'staging',
    }
    # default to dev if NOTIFY_ENVIRONMENT isn't provided
    img_env = env_map.get(os.environ.get('NOTIFY_ENVIRONMENT'), 'dev')
    return f'https://{img_env}-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png'


def insert_action_link(html: str) -> str:
    """
    Finds an action link and replaces it with the desired format. The action link is placed on it's own line, the link
    image is inserted into the link, and the styling is updated appropriately.
    """
    # common html used
    p_start = f'<p style="{PARAGRAPH_STYLE}">'
    p_end = '</p>'

    action_link_list = get_action_links(html)

    img_link = get_action_link_image_url()

    for item in action_link_list:
        # Puts the action link in a new <p> tag with appropriate styling.
        # item[0] and item[1] values will be '&gt;' symbols
        # item[2] is the html link <a ...> tag info
        # item[-1] is the link text and end of the link tag </a>
        action_link = (
            f'{item[2]}<img src="{img_link}" alt="call to action img" '
            f'style="vertical-align: middle;"> <b>{item[-1][:-4]}</b></a>'
        )

        action_link_p_tags = f'{p_start}{action_link}{p_end}'

        # get the text around the action link if there is any
        # ensure there are only two items in list with maxsplit
        before_link, after_link = html.split("".join(item), maxsplit=1)

        # value is the converted action link if there's nothing around it, otherwise <p> tags will need to be
        # closed / open around the action link
        if before_link == p_start and after_link == p_end:
            # action link exists on its own, unlikely to happen
            html = action_link_p_tags
        elif before_link.endswith(p_start) and after_link.startswith(p_end):
            # an action link on it's own line, as it should be
            html = f'{before_link}{action_link}{after_link}'
        elif before_link.endswith(p_start):
            # action link is on a newline, but has something after it on that line
            html = f'{before_link}{action_link}{p_end}{p_start}{after_link}'
        elif after_link == p_end:
            # paragraph ends with action link
            html = f'{before_link}{"</p>" if "<p" in before_link else ""}{action_link_p_tags}'
        else:
            # there's text before and after the action link within the paragraph
            html = (
                f'{before_link}{"</p>" if "<p" in before_link else ""}'
                f'{action_link_p_tags}'
                f'{p_start}{after_link}'
            )

    return html


def strip_parentheses_in_link_placeholders(value: str) -> str:
    """
    Captures markdown links with placeholders in them and replaces the parentheses around the placeholders with
    !! at the start and ## at the end. This makes them easy to put back after the convertion to html.

    Example Conversion:
    `[link text](http://example.com/((placeholder))) -> [link text](http://example.com/!!placeholder##)`

    Args:
        value (str): The email body to be processed

    Returns:
        str: The email body with the placeholders in markdown links with parentheses replaced with !! and ##
    """
    markdown_link_pattern = re.compile(r'\]\((.*?\({2}.*?\){2}.*?)+?\)')

    # find all markdown links with placeholders in them and replace the parentheses and html tags with !! and ##
    for item in re.finditer(markdown_link_pattern, value):
        link = item.group(0)
        # replace the opening parentheses with !!, include the opening span and mark tags if they exist
        modified_link = re.sub(r'((<span class=[\'\"]placeholder[\'\"]><mark>)?\(\((?![\(]))', '!!', link)
        # replace the closing parentheses with ##, include the closing span and mark tags if they exist
        modified_link = re.sub(r'(\)\)(<\/mark><\/span>)?)', '##', modified_link)

        value = value.replace(link, modified_link)

    return value


def replace_symbols_with_placeholder_parens(value: str) -> str:
    """
    Replaces the `!!` and `##` symbols with placeholder parentheses in the given string.

    Example Output: `!!placeholder## -> ((placeholder))`

    Args:
        value (str): The email body that has been converted from markdown to html

    Returns:
        str: The processed string with tags replaced by placeholder parentheses.
    """
    # pattern to find the placeholders surrounded by !! and ##
    placeholder_in_link_pattern = re.compile(r'(!![^()]+?##)')

    # find all instances of !! and ## and replace them with (( and ))
    for item in re.finditer(placeholder_in_link_pattern, value):
        placeholder = item.group(0)
        mod_placeholder = placeholder.replace('!!', '((')
        mod_placeholder = mod_placeholder.replace('##', '))')

        value = value.replace(placeholder, mod_placeholder)

    return value


def parse_hrule(block, m, state):
    """
    Parse a horizontal rule block.
    """
    # print("TEST 2")  # TODO - delete
    state.append_token({'type': 'hrule', 'raw': m.group('hrule_text')})
    return m.end() + 1


HRULE_PATTERN = r'''^(?P<hrule_text>[-*_]{3,})\s*$'''


def hrule(md):
    """
    A Mistune plug-in to recognize a horizontal rule.
        https://mistune.lepture.com/en/latest/advanced.html
        https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet#horizontal-rule
    """

    md.block.register('hrule', HRULE_PATTERN, parse_hrule)
    if md.renderer and md.renderer.NAME == 'html':
        # This Mistune docs recommend specifying default HTML renderers, but this is
        # is only used with plain text e-mail right now.
        pass
    # print("TEST 1")  # TODO - delete


class NotifyHTMLRenderer(HTMLRenderer):
    def link(self, text, url, title=None):
        value = super().link(text, url, title)
        # print('LINK', text, url, title, value) # TODO
        return value[:3] + f'style="{LINK_STYLE}"' + value[2:]

    def paragraph(self, text):
        value = super().paragraph(text)
        return value[:2] + f' style="{PARAGRAPH_STYLE}"' + value[2:]


class NotifyMarkdownRenderer(MarkdownRenderer):
    pass


notify_html_markdown = mistune.create_markdown(
    renderer=NotifyHTMLRenderer(),
    plugins=['url'],
)

notify_markdown = mistune.create_markdown(
    renderer=NotifyMarkdownRenderer(),
)

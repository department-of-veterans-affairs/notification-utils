import os
import string
import re
import urllib

import mistune
import bleach
from itertools import count
from markupsafe import Markup
from . import email_with_smart_quotes_regex
from notifications_utils.sanitise_text import SanitiseSMS
import smartypants

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


mistune._block_quote_leading_pattern = re.compile(r'^ *\^ ?', flags=re.M)
mistune.BlockGrammar.block_quote = re.compile(r'^( *\^[^\n]+(\n[^\n]+)*\n*)+')
mistune.BlockGrammar.list_block = re.compile(
    r'^( *)([•*-]|\d+\.)[\s\S]+?'
    r'(?:'
    r'\n+(?=\1?(?:[-*_] *){3,}(?:\n+|$))'  # hrule
    r'|\n+(?=%s)'  # def links
    r'|\n+(?=%s)'  # def footnotes
    r'|\n{2,}'
    r'(?! )'
    r'(?!\1(?:[•*-]|\d+\.) )\n*'
    r'|'
    r'\s*$)' % (
        mistune._pure_pattern(mistune.BlockGrammar.def_links),
        mistune._pure_pattern(mistune.BlockGrammar.def_footnotes),
    )
)
mistune.BlockGrammar.list_item = re.compile(
    r'^(( *)(?:[•*-]|\d+\.)[^\n]*'
    r'(?:\n(?!\2(?:[•*-]|\d+\.))[^\n]*)*)',
    flags=re.M
)
mistune.BlockGrammar.list_bullet = re.compile(r'^ *(?:[•*-]|\d+\.)')
mistune.InlineGrammar.url = re.compile(r'''^(https?:\/\/[^\s<]+[^<.,:"')\]\s])''')

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
url = re.compile(mistune.InlineGrammar.url.pattern[1:])


def unlink_govuk_escaped(message):
    return re.sub(
        govuk_not_a_link,
        r'\1' + '.\u200B' + r'\2',  # Unicode zero-width space
        message
    )


def nl2br(value):
    return re.sub(r'\n|\r', '<br>', value.strip())


def nl2li(value):
    return '<ul><li>{}</li></ul>'.format('</li><li>'.join(
        value.strip().split('\n')
    ))


def add_prefix(body, prefix=None):
    if prefix:
        return "{}: {}".format(prefix.strip(), body)
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
    return SanitiseSMS.encode(content)


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
        value
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
    return '{}\n'.format(value)


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


class NotifyLetterMarkdownPreviewRenderer(mistune.Renderer):

    def block_code(self, code, language=None):
        return code

    def block_quote(self, text):
        return text

    def header(self, text, level, raw=None):
        if level == 1:
            return super().header(text, 2)
        return self.paragraph(text)

    def hrule(self):
        return '<div class="page-break">&nbsp;</div>'

    def paragraph(self, text):
        if text.strip():
            return '<p>{}</p>'.format(text)
        return ''

    def table(self, header, body):
        return ""

    def autolink(self, link, is_email=False):
        return '<strong>{}</strong>'.format(
            link.replace('http://', '').replace('https://', '')
        )

    def codespan(self, text):
        return text

    def double_emphasis(self, text):
        return text

    def emphasis(self, text):
        return text

    def image(self, src, title, alt_text):
        return ""

    def linebreak(self):
        return "<br>"

    def newline(self):
        return self.linebreak()

    def list_item(self, text):
        return '<li>{}</li>\n'.format(text.strip())

    def link(self, link, title, content):
        return '{}: {}'.format(content, self.autolink(link))

    def strikethrough(self, text):
        return text

    def footnote_ref(self, key, index):
        return ""

    def footnote_item(self, key, text):
        return text

    def footnotes(self, text):
        return text


class NotifyEmailMarkdownRenderer(NotifyLetterMarkdownPreviewRenderer):

    def header(self, text, level, raw=None):
        if level == 1:
            return (
                '<h1 style="Margin: 0 0 20px 0; padding: 0; '
                'font-size: 32px; line-height: 35px; font-weight: bold; color: #323A45;">'
                '{}'
                '</h1>'
            ).format(
                text
            )
        elif level == 2:
            return (
                '<h2 style="Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45;'
                'font-size: 24px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;">'
                '{}'
                '</h2>'
            ).format(
                text
            )
        elif level == 3:
            return (
                '<h3 style="Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45;'
                'font-size: 20.8px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;">'
                '{}'
                '</h3>'
            ).format(
                text
            )
        return self.paragraph(text)

    def hrule(self):
        return (
            '<hr style="border: 0; height: 1px; background: #BFC1C3; Margin: 30px 0 30px 0;">'
        )

    def linebreak(self):
        return "<br />"

    def list(self, body, ordered=True):
        return (
            '<table role="presentation" style="padding: 0 0 20px 0;">'
            '<tr>'
            '<td style="font-family: Helvetica, Arial, sans-serif;">'
            '<ol style="Margin: 0 0 0 20px; padding: 0; list-style-type: decimal;">'
            '{}'
            '</ol>'
            '</td>'
            '</tr>'
            '</table>'
        ).format(
            body
        ) if ordered else (
            '<table role="presentation" style="padding: 0 0 20px 0;">'
            '<tr>'
            '<td style="font-family: Helvetica, Arial, sans-serif;">'
            '<ul style="Margin: 0 0 0 20px; padding: 0; list-style-type: disc;">'
            '{}'
            '</ul>'
            '</td>'
            '</tr>'
            '</table>'
        ).format(
            body
        )

    def list_item(self, text):
        return (
            '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px;'
            'line-height: 25px; color: #323A45;">'
            '{}'
            '</li>'
        ).format(
            text.strip()
        )

    def paragraph(self, text, is_inside_list=False):
        margin = 'Margin: 5px 0 5px 0' if is_inside_list else 'Margin: 0 0 20px 0'
        if text.strip():
            return f'<p style="{margin}; font-size: 16px; line-height: 25px; color: #323A45;">{text}</p>'
        return ""

    def block_quote(self, text):
        return (
            '<table '
            'width="100%" '
            'style="Margin: 0 0 20px 0; background: #F1F1F1;"'
            '>'
            '<td '
            'style="Padding: 24px 24px 0.1px 24px; font-family: Helvetica, Arial, sans-serif; '
            'font-size: 16px; line-height: 25px;"'
            '>'
            '{}'
            '</td>'
            '</table>'
        ).format(
            text
        )

    def link(self, link, title, content):
        return (
            '<a style="{}"{}{} target="_blank">{}</a>'
        ).format(
            LINK_STYLE,
            ' href="{}"'.format(link),
            ' title="{}"'.format(title) if title else "",
            content,
        )

    def autolink(self, link, is_email=False):
        if is_email:
            return link
        return '<a style="{}" href="{}">{}</a>'.format(
            LINK_STYLE,
            urllib.parse.quote(
                urllib.parse.unquote(link),
                safe=':/?#=&;'
            ),
            link
        )

    def double_emphasis(self, text):
        return '<strong>{}</strong>'.format(text)

    def emphasis(self, text):
        return '<em>{}</em>'.format(text)


class NotifyPlainTextEmailMarkdownRenderer(NotifyEmailMarkdownRenderer):

    COLUMN_WIDTH = 65

    def header(self, text, level, raw=None):
        if level == 1:
            return ''.join((
                self.linebreak() * 3,
                text,
                self.linebreak(),
                '-' * self.COLUMN_WIDTH,
            ))
        elif level in (2, 3):
            return ''.join((
                self.linebreak() * 2,
                text,
                self.linebreak(),
                '-' * self.COLUMN_WIDTH
            ))
        return self.paragraph(text)

    def hrule(self):
        return self.paragraph(
            '=' * self.COLUMN_WIDTH
        )

    def linebreak(self):
        return '\n'

    def list(self, body, ordered=True):

        def _get_list_marker():
            decimal = count(1)
            return lambda _: '{}.'.format(next(decimal)) if ordered else '•'

        return ''.join((
            self.linebreak(),
            re.sub(
                magic_sequence_regex,
                _get_list_marker(),
                body,
            ),
        ))

    def list_item(self, text):
        return ''.join((
            self.linebreak(),
            MAGIC_SEQUENCE,
            ' ',
            text.strip(),
        ))

    def paragraph(self, text, is_inside_list=False):
        if text.strip():
            return ''.join((
                self.linebreak() * 2,
                text,
            ))
        return ""

    def block_quote(self, text):
        return text

    def link(self, link, title, content):
        return ''.join((
            content,
            ' ({})'.format(title) if title else '',
            ': ',
            link,
        ))

    def autolink(self, link, is_email=False):
        return link

    def double_emphasis(self, text):
        return text

    def emphasis(self, text):
        return text


class NotifyEmailPreheaderMarkdownRenderer(NotifyPlainTextEmailMarkdownRenderer):

    def header(self, text, level, raw=None):
        return self.paragraph(text)

    def hrule(self):
        return ''

    def link(self, link, title, content):
        return ''.join((
            content,
            ' ({})'.format(title) if title else '',
        ))


class NotifyEmailBlockLexer(mistune.BlockLexer):

    def __init__(self, rules=None, **kwargs):
        super().__init__(rules, **kwargs)

    def parse_newline(self, m):
        if self._list_depth == 0:
            super().parse_newline(m)


class NotifyEmailMarkdown(mistune.Markdown):

    def __init__(self, renderer=None, inline=None, block=None, **kwargs):
        super().__init__(renderer, inline, block, **kwargs)
        self._is_inside_list = False

    def output_loose_item(self):
        body = self.renderer.placeholder()
        self._is_inside_list = True
        while self.pop()['type'] != 'list_item_end':
            body += self.tok()

        self._is_inside_list = False
        return self.renderer.list_item(body)

    def tok_text(self):
        if self._is_inside_list:
            return self.inline(self.token['text'])
        else:
            return super().tok_text()

    def output_text(self):
        return self.renderer.paragraph(self.tok_text(), self._is_inside_list)


notify_email_markdown = NotifyEmailMarkdown(
    renderer=NotifyEmailMarkdownRenderer(),
    block=NotifyEmailBlockLexer,
    hard_wrap=True,
    use_xhtml=False,
)
notify_plain_text_email_markdown = mistune.Markdown(
    renderer=NotifyPlainTextEmailMarkdownRenderer(),
    hard_wrap=True,
)
notify_email_preheader_markdown = mistune.Markdown(
    renderer=NotifyEmailPreheaderMarkdownRenderer(),
    hard_wrap=True,
)
notify_letter_preview_markdown = mistune.Markdown(
    renderer=NotifyLetterMarkdownPreviewRenderer(),
    hard_wrap=True,
    use_xhtml=False,
)

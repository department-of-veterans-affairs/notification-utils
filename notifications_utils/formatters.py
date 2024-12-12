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
from notifications_utils.action_link import action_link
from notifications_utils.sanitise_text import SanitiseSMS

BLOCK_QUOTE_STYLE = 'background: #F1F1F1; ' \
                    'padding: 24px 24px 0.1px 24px; ' \
                    'font-family: Helvetica, Arial, sans-serif; ' \
                    'font-size: 16px; line-height: 25px;'
COLUMN_WIDTH = 65
LINK_STYLE = 'word-wrap: break-word; color: #004795;'
ORDERED_LIST_STYLE = 'Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; ' \
                     'font-family: Helvetica, Arial, sans-serif;'
LIST_ITEM_STYLE = 'Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;'
PARAGRAPH_STYLE = 'Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;'
THEMATIC_BREAK_STYLE = 'border: 0; height: 1px; background: #BFC1C3; Margin: 30px 0 30px 0;'
UNORDERED_LIST_STYLE = 'Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: disk; ' \
                       'font-family: Helvetica, Arial, sans-serif;'

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


def add_prefix(body, prefix=None) -> str:
    if prefix:
        return f'{prefix.strip()}: {body}'
    return body


def autolink_sms(body):
    return url.sub(
        lambda match: '<a style="{}" target="_blank" href="{}">{}</a>'.format(
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
    """
    Calls to bleach.clean escapes HTML.  This function strips and escapes the input.
    """

    return bleach.clean(value, tags=[], strip=True)


def escape_html(value):
    """
    Calls to bleach.clean escapes HTML.  This function escapes, but does not strip, the input.
    """

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


class NotifyHTMLRenderer(HTMLRenderer):
    def action_link(self, text, url):
        raise NotImplementedError('MADE IT HERE')

    def block_quote(self, text):
        value = super().block_quote(text)
        return value[:11] + f' style="{BLOCK_QUOTE_STYLE}"' + value[11:]

    def heading(self, text, level, **attrs):
        if level == 1:
            style = 'Margin: 0 0 20px 0; padding: 0; font-size: 32px; ' \
                    'line-height: 35px; font-weight: bold; color: #323A45;'
        elif level == 2:
            style = 'Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45;' \
                    'font-size: 24px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;'
        elif level == 3:
            style = 'Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45;' \
                    'font-size: 20.8px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;'
        else:
            return self.paragraph(text)

        value = super().heading(text, level, **attrs)
        return value[:3] + f' style="{style}"' + value[3:]

    def image(self, alt, url, title=None):
        """
        Delete images.  VA e-mail messages contain only 1 image that is not managed by clients.
        """

        return ''

    def link(self, text, url, title=None):
        """
        Add CSS to links.
        """

        value = super().link(text, url, title)
        return value[:2] + f' style="{LINK_STYLE}" target="_blank"' + value[2:]

    def list(self, text, ordered, **attrs):
        value = super().list(text, ordered, **attrs)
        style = ORDERED_LIST_STYLE if ordered else UNORDERED_LIST_STYLE
        return value[:3] + f' role="presentation" style="{style}"' + value[3:]

    def list_item(self, text, **attrs):
        value = super().list_item(text, **attrs)
        return value[:3] + f' style="{LIST_ITEM_STYLE}"' + value[3:]

    def paragraph(self, text):
        """
        Add CSS to paragraphs.
        """

        value = super().paragraph(text)

        if value == '<p></p>\n':
            # This is the case when all child elements, such as tables and images, are deleted.
            return ''

        return value[:2] + f' style="{PARAGRAPH_STYLE}"' + value[2:]

    def table(self, text):
        """
        Delete tables.
        """

        # TODO - This is the expected test behavior, but it doesn't make sense.
        return ''

    def thematic_break(self):
        """
        Thematic breaks were known as horizontal rules (hrule) in earlier versions of Mistune.
        """

        value = super().thematic_break()
        return value[:3] + f' style="{THEMATIC_BREAK_STYLE}"' + value[3:]


class NotifyMarkdownRenderer(MarkdownRenderer):
    def block_quote(self, token, state):
        return '\n\n' + super().block_quote(token, state)[2:]

    def heading(self, token, state):
        level = token['attrs']['level']

        if level > 3:
            token['type'] = 'paragraph'
            return self.paragraph(token, state)

        value = super().heading(token, state)
        indentation = 3 if level == 1 else 2
        return ('\n' * indentation) + value.strip('#\n ') + '\n' + ('-' * COLUMN_WIDTH)

    def image(self, token, state):
        """
        Delete images.  VA e-mail messages contain only 1 image that is not managed by clients.
        """

        return ''

    def list(self, token, state):
        """
        Use the bullet character as the actual bullet output for all input (asterisks, pluses, and minues).
        """

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

        # TODO - This is the expected test behavior, but it doesn't make sense.
        return ''

    def thematic_break(self, token, state):
        """
        Thematic breaks were known as horizontal rules (hrule) in earlier versions of Mistune.
        """

        return '=' * COLUMN_WIDTH + '\n'


notify_html_markdown = mistune.create_markdown(
    hard_wrap=True,
    renderer=NotifyHTMLRenderer(escape=False),
    plugins=[action_link, 'strikethrough', 'table', 'url'],
)

notify_markdown = mistune.create_markdown(
    renderer=NotifyMarkdownRenderer(),
    plugins=['strikethrough', 'table'],
)

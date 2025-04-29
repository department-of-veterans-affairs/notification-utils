import re

import mistune
from mistune.renderers.html import HTMLRenderer

from notifications_utils.formatters import get_action_link_image_url


ACTION_LINK_PATTERN = re.compile(
    # Matches a Markdown-style action link: >>[text](url)
    # Example: >>[Action](https://example.com)
    r'(>|&gt;){2}'   # match exactly two '>' symbols, either literal '>' or HTML-encoded '&gt;'
    r'\['            # opening square bracket for link text
    r'([^\]]+)'      # capture group: link text (allows any character except ']')
    r'\]'            # closing square bracket
    r'\('            # opening parenthesis for URL
    r'(\S+)'         # capture group: URL (non-whitespace characters only; assumes pre-encoded)
    r'\)'            # closing parenthesis
)


def insert_action_links(markdown: str, as_html: bool = True) -> str:
    """
    Finds an "action link," and replaces it with the desired format. This preprocessing should take place before
    any manipulation by Mistune.  The CSS class "action_link" should be defined in a Jinja2 template.

    Given:
        >>[text](url)

    HTML Output:
        \n\n<a href="url"><img alt="call to action img" src="..." class="action_link"><b>text</b></a>\n\n

    For plain text, this function converts the action link to an ordinary link.  As with HTML output,
    text after the link will break to the next line.
    """

    if as_html:
        img_src = get_action_link_image_url()
        substitution = r'\n\n<a href="\3">' \
                       fr'<img alt="call to action img" src="{img_src}" class="action_link">' \
                       r'<b>\2</b></a>\n\n'
    else:
        substitution = r'\n\n[\2](\3)\n\n'

    return ACTION_LINK_PATTERN.sub(substitution, markdown)


class NotifyHTMLRenderer(HTMLRenderer):
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


notify_html_markdown = mistune.create_markdown(
    hard_wrap=True,
    renderer=NotifyHTMLRenderer(escape=False),
    plugins=['strikethrough', 'table', 'url'],
)

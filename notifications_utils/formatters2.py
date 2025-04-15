import mistune
from mistune.renderers.html import HTMLRenderer


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
    plugins=['strikethrough', 'table'],
    # plugins=['strikethrough', 'table', 'url'],
)

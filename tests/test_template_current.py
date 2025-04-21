from os import scandir
from typing import Generator

import pytest

from notifications_utils.formatters import (
    insert_action_link,
    insert_block_quotes,
    notify_markdown,
    notify_html_markdown,
)
from notifications_utils.template import get_html_email_body, PlainTextEmailTemplate


def generate_markdown_test_files() -> Generator[str, None, None]:
    """
    Yield the names of the markdown files in tests/test_files/markdown/.
    Do not yield subdirectories or their files.
    """

    for f in scandir('tests/test_files/markdown/'):
        if f.is_file():
            if f.name in ('action_links.md', 'block_quotes.md', 'block_quotes_action_link.md'):
                # These inputs are tested separately from the tests that use this generator
                # function because the markdown first requires a preprocessing step.  See the
                # TestRenderNotifyMarkdownWithPreprocessing test class below.
                continue

            yield f.name


@pytest.mark.parametrize('filename', generate_markdown_test_files())
def test_markdown_to_plain_text(filename: str):
    """
    Compare rendered Notify markdown with the expected plain text output.  This tests
    templates that do not have placeholders and do not require preprocessing.
    """

    if filename in ('images.md', 'lists.md'):
        pytest.xfail('This is known to be broken.')

    # Read the input markdown file.
    with open(f'tests/test_files/markdown/{filename}') as f:
        md = f.read()

    # Read the expected plain text file.
    with open(f'tests/test_files/plain_text/{filename[:-2]}txt') as f:
        expected = f.read()

    assert notify_markdown(md) == expected


@pytest.mark.parametrize('filename', generate_markdown_test_files())
def test_markdown_to_html(filename: str):
    """
    Compare rendered Notify markdown with the expected HTML output.  This tests
    templates that do not have placeholders and do not require preprocessing.
    """

    if filename in ('images.md', 'lists.md'):
        pytest.xfail('This is known to be broken.')

    # Read the input markdown file.
    with open(f'tests/test_files/markdown/{filename}') as f:
        md = f.read()

    # Read the expected HTML file.
    with open(f'tests/test_files/html_current/{filename[:-2]}html') as f:
        expected = f.read()

    assert notify_html_markdown(md) == expected


class TestRenderNotifyMarkdownWithPreprocessing:
    """
    These tests mirror the preprocessing behavior of template.py and formatters.py for markdown
    that otherwise would not be recognizable to Mistune.
    """

    @pytest.fixture(scope='class')
    def action_links_md_preprocessed(self) -> str:
        with open('tests/test_files/markdown/action_links.md') as f:
            return insert_action_link(f.read())

    @pytest.fixture(scope='class')
    def block_quotes_md_preprocessed(self) -> str:
        with open('tests/test_files/markdown/block_quotes.md') as f:
            return insert_block_quotes(f.read())

    @pytest.fixture(scope='class')
    def block_quotes_action_link_md(self) -> str:
        with open('tests/test_files/markdown/block_quotes_action_link.md') as f:
            return f.read()

    ###############################
    # Action links
    ###############################

    def test_action_links_html(self, action_links_md_preprocessed: str):
        # Read the expected HTML file.
        with open('tests/test_files/html_current/action_links.html') as f:
            expected = f.read()

        assert notify_html_markdown(action_links_md_preprocessed) == expected

    @pytest.mark.skip(reason='Action links are not implemented for plain text.')
    def test_action_links_plain_text(self, action_links_md_preprocessed: str):
        # Read the expected plain text file.
        with open('tests/test_files/plain_text/action_links.txt') as f:
            expected = f.read()

        assert notify_markdown(action_links_md_preprocessed) == expected

    ###############################
    # Block quotes
    ###############################

    # Notify uses the nonstandard "^" to denote a block quote.

    @pytest.mark.xfail(reason='#203')
    def test_block_quotes_html(self, block_quotes_md_preprocessed: str):
        # Read the expected HTML file.
        with open('tests/test_files/html_current/block_quotes.html') as f:
            expected = f.read()

        assert notify_html_markdown(block_quotes_md_preprocessed) == expected

    @pytest.mark.xfail(reason='#203')
    def test_block_quotes_plain_text(self, block_quotes_md_preprocessed: str):
        # Read the expected plain text file.
        with open('tests/test_files/plain_text/block_quotes.txt') as f:
            expected = f.read()

        assert notify_markdown(block_quotes_md_preprocessed) == expected

    ###############################
    # Block quotes with action link
    ###############################

    def test_block_quotes_action_link_html(self, block_quotes_action_link_md: str):
        # This order of operations mirrors the behavior in template.py::get_html_email_body.
        md = insert_block_quotes(block_quotes_action_link_md)
        md = insert_action_link(md)
        # Read the expected HTML file.
        with open('tests/test_files/html_current/block_quotes_action_link.html') as f:
            expected = f.read()
        assert notify_html_markdown(md) == expected

    @pytest.mark.skip(reason='Action links are not implemented for plain text.')
    def test_block_quotes_action_link_plain_text(self, block_quotes_action_link_md: str):
        # This order of operations mirrors the behavior in template.py::PlainTextEmailTemplate.__str__.
        # Note that the is no insertion of actions links yet.
        md = insert_block_quotes(block_quotes_action_link_md)

        # Read the expected plain text file.
        with open('tests/test_files/plain_text/block_quotes_action_link.txt') as f:
            expected = f.read()

        assert notify_markdown(md) == expected


class TestRenderNotifyMarkdownLinksPlaceholders:
    """
    links_placeholders.md has these personalizations: url, url_fragment, url_text, and yt_video_id.
    """

    @pytest.fixture(scope='class')
    def md(self) -> str:
        with open('tests/test_files/markdown/placeholders/links_placeholders.md') as f:
            return f.read()

    @pytest.mark.parametrize(
        'personalization, suffix',
        (
            (
                {
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'url_fragment': 'va',
                    'url_text': 'click',
                    'yt_video_id': 'dQw4w9WgXcQ',
                },
                'simple',
            ),
            (
                {
                    'url': 'https://www.example.com/watch?t=abc def',
                    'url_fragment': 'the va',
                    'url_text': 'click this',
                    'yt_video_id': 'dQw4w   9WgXcQ',
                },
                'spaces',
            ),
            (
                {
                    'url': 'https://www.example.com/watch?t=abc\tdef',
                    'url_fragment': 'the\tva',
                    'url_text': 'click this',
                    'yt_video_id': 'dQw4w\t\t\t9WgXcQ',
                },
                'tabs',
            ),
        ),
        ids=(
            # No special characters or spaces.  Verbatim substitution.
            'simple',
            # Personalization has spaces.  URL safe encoding, when applicable.
            'spaces',
            # Link personalization has tabs.  URL safe encoding, when applicable.
            'tabs',
        )
    )
    @pytest.mark.parametrize('as_html', (True, False))
    def test_placeholders(self, as_html, personalization, suffix, md):
        """
        Substitute the given personalization, render the template, and compare the output with
        the expected output.  All spaces in URLs should be URL safe encoded so the presentation
        is correct.  It is the users' responsibility to ensure a link is valid.
        """

        if as_html:
            expected_filename = f'tests/test_files/html_current/placeholders/links_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/links_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        if as_html:
            assert get_html_email_body(md, personalization) == expected
        else:
            template = PlainTextEmailTemplate({'content': md, 'subject': ''}, personalization)
            assert str(template) == expected


class TestRenderNotifyMarkdownActionLinksPlaceholders:
    """
    action_links_placeholders.md has these personalizations: url, url_text, and yt_video_id.
    """

    @pytest.fixture(scope='class')
    def md(self) -> str:
        with open('tests/test_files/markdown/placeholders/action_links_placeholders.md') as f:
            return f.read()

    @pytest.mark.parametrize(
        'personalization, suffix',
        (
            (
                {
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'url_text': 'click',
                    'yt_video_id': 'dQw4w9WgXcQ',
                },
                'simple',
            ),
            (
                {
                    'url': 'https://www.example.com/watch?t=abc def',
                    'url_text': 'click this',
                    'yt_video_id': 'dQw4w   9WgXcQ',
                },
                'spaces',
            ),
            (
                {
                    'url': 'https://www.example.com/watch?t=abc\tdef',
                    'url_text': 'click this',
                    'yt_video_id': 'dQw4w\t\t\t9WgXcQ',
                },
                'tabs',
            ),
        ),
        ids=(
            # No special characters or spaces.  Verbatim substitution.
            'simple',
            # Personalization has spaces.  URL safe encoding, when applicable.
            'spaces',
            # Link personalization has tabs.  URL safe encoding, when applicable.
            'tabs',
        )
    )
    @pytest.mark.parametrize('as_html', (True, False))
    def test_placeholders(self, as_html, personalization, suffix, md):
        """
        Substitute the given personalization, render the template, and compare the output with
        the expected output.  All spaces in URLs should be URL safe encoded so the presentation
        is correct.  It is the users' responsibility to ensure a link is valid.
        """

        if not as_html:
            pytest.xfail('Action links are not implemented for plain text.')

        if as_html:
            expected_filename = f'tests/test_files/html_current/placeholders/action_links_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/action_links_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        if as_html:
            assert get_html_email_body(md, personalization) == expected
        else:
            template = PlainTextEmailTemplate({'content': md, 'subject': ''}, personalization)
            assert str(template) == expected


@pytest.mark.xfail(reason='#203')
class TestRenderNotifyMarkdownBlockQuotesPlaceholders:
    """
    block_quotes_placeholders.md has these personalizations: bottom, claims, nested, and top.
    """

    @pytest.fixture(scope='class')
    def md(self) -> str:
        with open('tests/test_files/markdown/placeholders/block_quotes_placeholders.md') as f:
            return f.read()

    @pytest.mark.parametrize(
        'personalization, suffix',
        (
            (
                {
                    'bottom': 'C',
                    'claims': 'one, two, three',
                    'nested': 'B',
                    'top': 'A',
                },
                'simple',
            ),
            (
                {
                    'bottom': ['G', 'H', 'I'],
                    'claims': ['one', 'two', 'three'],
                    'nested': ['D', 'E', 'F'],
                    'top': ['A', 'B', 'C'],
                },
                'lists',
            ),
        ),
        ids=(
            # Verbatim substitution.
            'simple',
            # Substituting lists into a block quote should not terminate the block quote prematurely.
            'lists',
        )
    )
    @pytest.mark.parametrize('as_html', (True, False))
    def test_placeholders(self, as_html, personalization, suffix, md):
        """
        Substitute the given personalization, render the template, and compare the output with
        the expected output.
        """

        if as_html:
            expected_filename = f'tests/test_files/html_current/placeholders/block_quotes_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/block_quotes_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        if as_html:
            assert get_html_email_body(md, personalization) == expected
        else:
            template = PlainTextEmailTemplate({'content': md, 'subject': ''}, personalization)
            assert str(template) == expected

from os import scandir
from typing import Generator

import pytest

from notifications_utils.formatters import (
    insert_action_link,
    notify_markdown,
    notify_html_markdown,
)


def generate_markdown_test_files() -> Generator[str, None, None]:
    """
    Yield the names of the markdown files in tests/test_files/markdown/.
    Do not yield subdirectories or their files.
    """

    for f in scandir('tests/test_files/markdown/'):
        if f.is_file():
            yield f.name


@pytest.mark.parametrize('filename', generate_markdown_test_files())
def test_markdown_to_plain_text(filename: str):
    """
    Compare rendered Notify markdown with the expected plain text output.  This tests
    templates that do not have placeholders.
    """

    if filename in ('images.md', 'lists.md'):
        pytest.xfail('This is known to be broken.')
    elif filename == 'action_links.md':
        pytest.skip('Actions links require pre-processing and are tested elsewhere.')

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
    templates that do not have placeholders.
    """

    if filename in ('images.md', 'lists.md'):
        pytest.xfail('This is known to be broken.')
    elif filename == 'action_links.md':
        pytest.skip('Actions links require pre-processing and are tested elsewhere.')

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

    def test_action_links_html(self, action_links_md_preprocessed: str):
        # Read the expected HTML file.
        with open('tests/test_files/html_current/action_links.html') as f:
            expected = f.read()

        assert notify_html_markdown(action_links_md_preprocessed) == expected

    @pytest.mark.xfail(reason='Action links are not expected to work correctly with plain text.')
    def test_action_links_plain_text(self, action_links_md_preprocessed: str):
        # Read the expected plain text file.
        with open('tests/test_files/plain_text/action_links.txt') as f:
            expected = f.read()

        assert notify_markdown(action_links_md_preprocessed) == expected


@pytest.mark.skip
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
                    'url_fragment': 'theonion',
                    'url_text': 'click',
                    'yt_video_id': 'dQw4w9WgXcQ',
                },
                'simple',
            ),
            (
                {
                    'url': 'https://www.example.com/watch?t=abc def',
                    'url_fragment': 'the onion',
                    'url_text': 'click this',
                    'yt_video_id': 'dQw4w   9WgXcQ',
                },
                'spaces',
            ),
        ),
        ids=(
            # No special characters or spaces.  Verbatim substitution.
            'simple',
            # Personalization has spaces.  URL safe encoding, when applicable.
            'spaces',
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

        # assert render_notify_markdown(md, personalization, as_html) == expected
        raise NotImplementedError


@pytest.mark.skip
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
        ),
        ids=(
            # No special characters or spaces.  Verbatim substitution.
            'simple',
            # Personalization has spaces.  URL safe encoding, when applicable.
            'spaces',
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
            expected_filename = f'tests/test_files/html_current/placeholders/action_links_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/action_links_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        # assert render_notify_markdown(md, personalization, as_html) == expected
        raise NotImplementedError


@pytest.mark.skip
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

        # assert render_notify_markdown(md, personalization, as_html) == expected
        raise NotImplementedError

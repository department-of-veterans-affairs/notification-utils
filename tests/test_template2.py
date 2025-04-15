# from os import scandir
from typing import Generator

import pytest

from notifications_utils.template2 import render_notify_markdown


def generate_markdown_test_files() -> Generator[str, None, None]:
    """
    Yield the names of the markdown files in tests/test_files/markdown/.
    Do not yield subdirectories or their files.
    """

    # TODO - When all inputs are expected to pass, remove these individual yields, and restore the subsequent loop.
    yield 'headers.md'
    yield 'emphasis.md'
    yield 'images.md'
    yield 'tables.md'
    yield 'thematic_break.md'

    # TODO - This code will be restored during tickets that follow #213.
    # for f in scandir('tests/test_files/markdown/'):
    #     if f.is_file():
    #         yield f.name


@pytest.mark.parametrize('as_html', (True, False))
@pytest.mark.parametrize('filename', generate_markdown_test_files())
def test_render_notify_markdown(filename: str, as_html: bool):
    """
    Compare rendered Notify markdown with the expected output.  This tests all the
    templates that do not have placeholders.
    """

    # Read the input markdown file.
    with open(f'tests/test_files/markdown/{filename}') as f:
        md = f.read()

    if as_html:
        expected_filename = f'tests/test_files/html/{filename[:-2]}html'
    else:
        expected_filename = f'tests/test_files/plain_text/{filename[:-2]}txt'

    # Read the expected HTML or plain text file.
    with open(expected_filename) as f:
        expected = f.read()

    assert render_notify_markdown(md, as_html=as_html) == expected


@pytest.mark.skip(reason='not implemented')
def test_render_notify_markdown_missing_personalization():
    """
    Calling render_notify_markdown without all of the personalizations should raise
    ValueError.
    """

    with pytest.raises(ValueError, match='missing required personalization'):
        render_notify_markdown('This is ((test)) markdown.')


@pytest.mark.skip(reason='not implemented')
def test_render_notify_markdown_extra_personalization():
    """
    Calling render_notify_markdown with more than the required personalizations should
    not raise an exception.  This is also a simple happy path test.
    """

    md = 'This is ((test)) markdown.'
    plain_text = 'This is some markdown.\n'

    assert render_notify_markdown(md, {'test': 'some', 'extra': 'extra'}, False) == plain_text


@pytest.mark.skip(reason='not implemented')
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
    def test_placeholders(self, as_html: bool, personalization: dict, suffix: str, md: str):
        """
        Substitute the given personalization, render the template, and compare the output with
        the expected output.  All spaces in URLs should be URL safe encoded so the presentation
        is correct.  It is the users' responsibility to ensure a link is valid.
        """

        if as_html:
            expected_filename = f'tests/test_files/html/placeholders/links_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/links_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        assert render_notify_markdown(md, personalization, as_html) == expected


@pytest.mark.skip(reason='not implemented')
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
    def test_placeholders(self, as_html: bool, personalization: dict, suffix: str, md: str):
        """
        Substitute the given personalization, render the template, and compare the output with
        the expected output.  All spaces in URLs should be URL safe encoded so the presentation
        is correct.  It is the users' responsibility to ensure a link is valid.
        """

        if as_html:
            expected_filename = f'tests/test_files/html/placeholders/action_links_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/action_links_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        assert render_notify_markdown(md, personalization, as_html) == expected


@pytest.mark.skip(reason='not implemented')
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
    def test_placeholders(self, as_html: bool, personalization: dict, suffix: str, md: str):
        """
        Substitute the given personalization, render the template, and compare the output with
        the expected output.
        """

        if as_html:
            expected_filename = f'tests/test_files/html/placeholders/block_quotes_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/block_quotes_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        assert render_notify_markdown(md, personalization, as_html) == expected

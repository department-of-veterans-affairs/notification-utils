from os import scandir
from typing import Generator

import pytest

from notifications_utils.template2 import make_substitutions_in_subject, render_notify_markdown


def generate_markdown_test_files() -> Generator[str, None, None]:
    """
    Yield the names of the markdown files in tests/test_files/markdown/.
    Do not yield subdirectories or their files.
    """

    for f in scandir('tests/test_files/markdown/'):
        if f.is_file():
            yield f.name


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


def test_render_notify_markdown_missing_personalization():
    """
    Calling render_notify_markdown without all of the personalizations should raise ValueError.
    """

    with pytest.raises(ValueError, match='Missing required personalization: test2'):
        render_notify_markdown('This is ((test1)) markdown ((test2)).', {'test1': 'test'})


def test_render_notify_markdown_empty_personalization():
    """
    An empty personalization dictionary should not raise an exception.
    """

    render_notify_markdown('This is ((test1)) markdown ((test2)).', {})


def test_render_notify_markdown_extra_personalization():
    """
    Calling render_notify_markdown with more than the required personalizations should
    not raise an exception.  This is also a simple happy path test.
    """

    md = 'This is ((test)) markdown.'
    plain_text = 'This is some markdown.\n'

    assert render_notify_markdown(md, {'test': 'some', 'extra': 'extra'}, False) == plain_text


class TestRenderNotifyMarkdownHeadersPlaceholders:
    """
    headers_placeholders.md has the personalizations p1, p2, and p3.
    """

    @pytest.fixture(scope='class')
    def md(self) -> str:
        with open('tests/test_files/markdown/placeholders/headers_placeholders.md') as f:
            return f.read()

    @pytest.mark.parametrize(
        'personalization, suffix',
        (
            (None, 'none'),
            (
                {
                    'p1': 'there',
                    'p2': 'This is an H2',
                    'p3': 'test',
                },
                'simple',
            ),
            (
                {
                    'p1': 'there',
                    'p2': 'This is an H2',
                    'p3': ['A', 'B', 'C'],
                },
                'lists',
            ),
        ),
        ids=(
            # No substitution.
            'none',
            # No list values.
            'simple',
            # List values.
            'lists',
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
            expected_filename = f'tests/test_files/html/placeholders/headers_placeholders_{suffix}.html'
        else:
            expected_filename = f'tests/test_files/plain_text/placeholders/headers_placeholders_{suffix}.txt'

        with open(expected_filename) as f:
            expected = f.read()

        assert render_notify_markdown(md, personalization, as_html) == expected


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
                    'url_fragment': 'the va',
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
            'tabs',
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
            'tabs',
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
                    'bottom': 'B',
                    'claims': 'one, two, three',
                    'top': 'A',
                },
                'simple',
            ),
            (
                {
                    'bottom': ['D', 'E', 'F'],
                    'claims': ['one', 'two', 'three'],
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


@pytest.mark.parametrize(
    'content, expected',
    (
        (
            'Hello, ((name))!',
            '<p style="margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">Hello, <mark>((name))</mark>!</p>\n',  # noqa E501
        ),
        (
            '1. placeholder in link text: [link text ((link_text))](https://test.com)',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholder in link text: '  # noqa E501
            '<a href="https://test.com">link text <mark>((link_text))</mark></a>'
            '</li>\n'
            '</ol>\n',
        ),
        (
            '2. placeholder at end of URL: [link text](https://test.com/((url_path_fragment)))',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="2">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholder at end of URL: '  # noqa E501
            '<a href="https://test.com/((url_path_fragment))">link text</a>'
            '</li>\n'
            '</ol>\n',
        ),
        (
            '3. placeholder at start of URL: [link text](((url_prefix))test.com)',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="3">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholder at start of URL: '  # noqa E501
            '<a href="((url_prefix))test.com">link text</a>'
            '</li>\n'
            '</ol>\n',
        ),
        (
            '4. placeholder in middle of URL: [link text](https://((url_domain_fragment))-test.com)',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="4">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholder in middle of URL: '  # noqa E501
            '<a href="https://((url_domain_fragment))-test.com">link text</a>'
            '</li>\n'
            '</ol>\n',
        ),
        (
            '5. placeholder for URL: [link text](((url)))',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="5">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholder for URL: <a href="((url))">link text</a></li>\n'  # noqa E501
            '</ol>\n',
        ),
        (
            '6. placeholders in middle of URL and as a query parameter: '
            '[link text](https://((url_domain_fragment))-test.com?x=((query_param)))',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="6">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholders in middle of URL and as a query parameter: '  # noqa E501
            '<a href="https://((url_domain_fragment))-test.com?x=((query_param))">link text</a>'
            '</li>\n'
            '</ol>\n',
        ),
        (
            '7. placeholders in link text and end of URL: '
            '[link ((link_text)) text](https://test.com/((url_path_fragment)))',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="7">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholders in link text and end of URL: '  # noqa E501
            '<a href="https://test.com/((url_path_fragment))">link <mark>((link_text))</mark> text</a>'
            '</li>\n'
            '</ol>\n',
        ),
        (
            '8. placeholders in middle of URL and multiple query parameters: '
            '[link text](https://((url_domain_fragment))-test.com?x=((query_param))&y=((query_param)))',
            '<ol role="presentation" style="margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; font-family: Helvetica, Arial, sans-serif;" start="8">\n'  # noqa E501
            '<li style="margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">placeholders in middle of URL and multiple query parameters: '  # noqa E501
            '<a href="https://((url_domain_fragment))-test.com?x=((query_param))&amp;y=((query_param))">link text</a>'
            '</li>\n'
            '</ol>\n',
        ),
    ),
    ids=(
        'simple',
        'placeholder in link text',
        'placeholder at end of URL',
        'placeholder at start of URL',
        'placeholder in middle of URL',
        'placeholder for URL',
        'placeholders in middle of URL and as a query parameter',
        'placeholders in link text and end of URL',
        'placeholders in middle of URL and multiple query parameters',
    )
)
def test_render_notify_markdown_preview_mode(content, expected):
    """
    Placeholders in preview should be wrapped with the "mark" HTML element unless they are part of a URL.
    """

    assert render_notify_markdown(content, preview_mode=True) == expected


def test_make_substitutions_in_subject():
    """
    Test the happy path.  Extra values should not cause a problem.
    """

    subject = 'Hello, ((name))!'
    assert make_substitutions_in_subject(subject, {'name': 'Bob', 'other': ['one', 'two']}) == 'Hello, Bob!'


def test_make_substitutions_in_subject_missing_value():
    subject = 'Hello, ((name))!  Happy ((day)).'

    with pytest.raises(ValueError, match='Missing required subject personalization: name, day'):
        make_substitutions_in_subject(subject, {'not_name': 'uh oh'})


def test_make_substitutions_in_subject_none_value():
    subject = 'Hello, ((name))!'

    with pytest.raises(ValueError, match='Missing required subject personalization: name'):
        make_substitutions_in_subject(subject, {'name': None})

import pytest
from markupsafe import Markup

from notifications_utils.formatters import (
    escape_html,
    formatted_list,
    insert_list_spaces,
    make_quotes_smart,
    nl2li,
    normalise_whitespace,
    notify_html_markdown,
    notify_markdown,
    remove_smart_quotes_from_email_addresses,
    remove_whitespace_before_punctuation,
    replace_hyphens_with_en_dashes,
    sms_encode,
    strip_and_remove_obscure_whitespace,
    strip_dvla_markup,
    strip_pipes,
    strip_unsupported_characters,
    strip_whitespace,
    tweak_dvla_list_markup,
)
from notifications_utils.template import (
    HTMLEmailTemplate,
    SMSMessageTemplate,
    SMSPreviewTemplate
)

PARAGRAPH_TEXT = '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">{}</p>\n'


@pytest.mark.parametrize(
    "url", [
        "http://example.com",
        "http://www.gov.uk/",
        "https://www.gov.uk/",
        "http://service.gov.uk",
    ]
)
def test_makes_links_out_of_urls(url):
    link = f'<a style="word-wrap: break-word; color: #004795;" target="_blank" href="{url}">{url}</a>'
    assert notify_html_markdown(url) == PARAGRAPH_TEXT.format(link)


@pytest.mark.parametrize('input_text, output', [
    (
        (
            'this is some text with a link http://example.com in the middle'
        ),
        (
            'this is some text with a link '
            '<a style="word-wrap: break-word; color: #004795;" target="_blank" '
            'href="http://example.com">http://example.com</a>'
            ' in the middle'
        ),
    ),
    (
        (
            'this link is in brackets (http://example.com)'
        ),
        (
            'this link is in brackets '
            '(<a style="word-wrap: break-word; color: #004795;" target="_blank" '
            'href="http://example.com">http://example.com</a>)'
        ),
    )
])
def test_makes_links_out_of_urls_in_context(input_text, output):
    assert notify_html_markdown(input_text) == PARAGRAPH_TEXT.format(output)


@pytest.mark.parametrize(
    "url", [
        "example.com",
        "www.example.com",
        "ftp://example.com",
        "test@example.com",
        "mailto:test@example.com",
    ]
)
def test_makes_paragraphs_out_of_invalid_urls(url):
    assert notify_html_markdown(url) == PARAGRAPH_TEXT.format(url)


def test_handles_placeholders_in_urls():
    assert notify_html_markdown(
        "http://example.com/?token=<span class='placeholder'>((token))</span>&key=1"
    ) == (
        '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
        '<a style="word-wrap: break-word; color: #004795;" target="_blank" href="http://example.com/?token=">'
        'http://example.com/?token='
        '</a>'
        '<span class=\'placeholder\'>((token))</span>&amp;key=1'
        '</p>\n'
    )


@pytest.mark.parametrize(
    "url, expected_html, expected_html_in_template",
    [
        (
            """https://example.com"onclick="alert('hi')""",
            """<a style="word-wrap: break-word; color: #004795;" target="_blank" href="https://example.com%22onclick=%22alert(%27hi">https://example.com&quot;onclick=&quot;alert('hi</a>')""",  # noqa
            """<a style="word-wrap: break-word; color: #004795;" target="_blank" href="https://example.com%22onclick=%22alert(%27hi">https://example.com&quot;onclick=&quot;alert('hi</a>‘)""",  # noqa
        ),
        (
            """https://example.com"style='text-decoration:blink'""",
            """<a style="word-wrap: break-word; color: #004795;" target="_blank" href="https://example.com%22style=%27text-decoration:blink">https://example.com&quot;style='text-decoration:blink</a>'""",  # noqa
            """<a style="word-wrap: break-word; color: #004795;" target="_blank" href="https://example.com%22style=%27text-decoration:blink">https://example.com&quot;style='text-decoration:blink</a>’""",  # noqa
        ),
    ],
    ids=['js', 'style']
)
def test_urls_get_escaped(url, expected_html, expected_html_in_template):
    assert notify_html_markdown(url) == (PARAGRAPH_TEXT).format(expected_html)
    assert expected_html_in_template in str(HTMLEmailTemplate({'content': url, 'subject': ''}))


def test_html_template_has_urls_replaced_with_links():
    assert (
        '<a style="word-wrap: break-word; color: #004795;" target="_blank" '
        'href="https://service.example.com/accept_invite/a1b2c3d4">https://service.example.com/accept_invite/a1b2c3d4'
        '</a>'
    ) in str(HTMLEmailTemplate({'content': (
        'You’ve been invited to a service. Click this link:\n'
        'https://service.example.com/accept_invite/a1b2c3d4\n'
        '\n'
        'Thanks\n'
    ), 'subject': ''}))


@pytest.mark.parametrize(
    'markdown_function, expected_output',
    [
        (notify_html_markdown, (
            '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
            '<a style="word-wrap: break-word; color: #004795;" target="_blank" href="https://example.com">'
            'https://example.com'
            '</a>'
            '</p>\n'
            '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
            'Next paragraph'
            '</p>\n'
        )),
        (notify_markdown, (
            'https://example.com\n\n'
            'Next paragraph\n'
        )),
    ],
    ids=('notify_html_markdown', 'notify_markdown'),
)
def test_preserves_whitespace_when_making_links(
    markdown_function, expected_output
):
    assert markdown_function(
        'https://example.com\n'
        '\n'
        'Next paragraph'
    ) == expected_output


@pytest.mark.parametrize(
    "prefix, body, expected", [
        ("a", "b", "a: b"),
        (None, "b", "b"),
    ]
)
def test_sms_message_adds_prefix(prefix, body, expected):
    template = SMSMessageTemplate({'content': body})
    template.prefix = prefix
    template.sender = None
    assert str(template) == expected


def test_sms_preview_adds_newlines():
    template = SMSPreviewTemplate({'content': """
        the
        quick

        brown fox
    """})
    template.prefix = None
    template.sender = None
    assert '<br>' in str(template)


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            '<pre><code>print(&quot;hello&quot;)\n</code></pre>\n'
        ],
        [
            notify_markdown,
            '```\nprint("hello")\n```\n'
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_block_code(markdown_function, expected):
    assert markdown_function('```\nprint("hello")\n```') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<blockquote style="background: #F1F1F1; padding: 24px 24px 0.1px 24px; '
                'font-family: Helvetica, Arial, sans-serif; font-size: 16px; line-height: 25px;">\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; '
                'line-height: 25px; color: #323A45;">inset text</p>\n</blockquote>\n'
            )
        ],
        [
            notify_markdown,
            '\n\ninset text\n'
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_block_quote(markdown_function, expected):
    assert markdown_function('> inset text') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<h1 style="Margin: 0 0 20px 0; padding: 0; font-size: 32px; '
                'line-height: 35px; font-weight: bold; color: #323A45;">'
                'heading'
                '</h1>\n'
            )
        ],
        [
            notify_markdown,
            (
                '\n'
                '\n'
                '\nheading'
                '\n-----------------------------------------------------------------\n'
            ),
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_level_1_header(markdown_function, expected):
    assert markdown_function('# heading') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            '<h2 style="Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45; '
            'font-size: 24px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;">inset text</h2>\n'
        ],
        [
            notify_markdown,
            (
                '\n'
                '\ninset text'
                '\n-----------------------------------------------------------------\n'
            ),
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_level_2_header(markdown_function, expected):
    assert markdown_function('## inset text') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            '<h3 style="Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45; '
            'font-size: 20.8px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;">inset text</h3>\n'
        ],
        [
            notify_markdown,
            (
                '\n'
                '\ninset text'
                '\n-----------------------------------------------------------------\n'
            ),
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_level_3_header(markdown_function, expected):
    assert markdown_function('### inset text') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">a</p>\n'
                '<hr style="border: 0; height: 1px; background: #BFC1C3; Margin: 30px 0 30px 0;" />\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">b</p>\n'
            )
        ],
        [
            notify_markdown,
            (
                'a\n\n'
                '=================================================================\n'
                'b\n'
            ),
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_thematic_break(markdown_function, expected):
    """
    Thematic breaks were known as horizontal rules (hrule) in earlier versions of Mistune.
    """

    assert markdown_function('a\n\n***\n\nb') == expected
    assert markdown_function('a\n\n---\n\nb') == expected


def test_ordered_list():
    assert notify_html_markdown(
        '1. one\n'
        '2. two\n'
        '3. three\n'
    ) == (
        '<ol role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; '
        'font-family: Helvetica, Arial, sans-serif;">\n'
        '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">'
        'one</li>\n'
        '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">'
        'two</li>\n'
        '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; line-height: 25px; color: #323A45;">'
        'three</li>\n'
        '</ol>\n'
    )


@pytest.mark.parametrize(
    'test_text, expected',
    (
        [
            (
                '1. List item 1\n\n'
                '\tShould be paragraph in the list item without extra br above'
            ),
            (
                '<ol role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">List item 1</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
                'Should be paragraph in the list item without extra br above</p>\n'
                '</li>\n'
                '</ol>\n'
            )
        ],
        [
            (
                '1. List item 1\n\n'
                ' Should not be paragraph in the list item without extra br above'
            ),
            (
                '<ol role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                'List item 1'
                '</li>\n'
                '</ol>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
                'Should not be paragraph in the list item without extra br above</p>\n'
            )
        ],
        [
            (
                '1. one'
                '\n\n nested 1'
                '\n\n nested 2'
                '\n1. two'
                '\n1. three'
            ),
            (
                '<ol role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                'one'
                '</li>\n'
                '</ol>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">nested 1</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">nested 2</p>\n'
                '<ol role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: decimal; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">two</li>\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">three</li>\n'
                '</ol>\n'
            )
        ],
        [
            (
                '* one'
                '\n\n nested 1'
                '\n\n nested 2'
                '\n* two'
                '\n* three'
            ),
            (
                '<ul role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: disc; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                'one'
                '</li>\n'
                '</ul>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">nested 1</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">nested 2</p>\n'
                '<ul role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; list-style-type: disc; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">two</li>\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">three</li>\n'
                '</ul>\n'
            )
        ],
    ),
    ids=['paragraph_in_list', 'paragraph_not_in_list', 'ordered_nested_list', 'unordered_nested_list']
)
def test_paragraph_in_list_has_no_linebreak(test_text, expected):
    assert notify_html_markdown(test_text) == expected


@pytest.mark.parametrize(
    'markdown',
    (
        (  # two spaces
            '*  one\n'
            '*  two\n'
            '*  three\n'
        ),
        (  # tab
            '*  one\n'
            '*  two\n'
            '*  three\n'
        ),
        (  # dash as bullet
            '- one\n'
            '- two\n'
            '- three\n'
        ),
        (  # plus as bullet
            '+ one\n'
            '+ two\n'
            '+ three\n'
        ),
    ),
    ids=['two_spaces', 'tab', 'dash_as_bullet', 'plus_as_bullet']
)
@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<ul role="presentation" style="Margin: 0 0 0 20px; padding: 0 0 20px 0; '
                'list-style-type: disc; '
                'font-family: Helvetica, Arial, sans-serif;">\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                'one</li>\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                'two</li>\n'
                '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 16px; '
                'line-height: 25px; color: #323A45;">'
                'three</li>\n'
                '</ul>\n'
            )
        ],
        [
            notify_markdown,
            '• one\n• two\n• three\n'
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_unordered_list(markdown, markdown_function, expected):
    assert markdown_function(markdown) == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">line one<br />\n'
                'line two</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">new paragraph</p>\n'
            )
        ],
        [
            notify_markdown,
            (
                'line one\n'
                'line two\n'
                '\nnew paragraph\n'
            ),
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_paragraphs(markdown_function, expected):
    assert markdown_function(
        'line one\n'
        'line two\n'
        '\n'
        'new paragraph'
    ) == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">before</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">after</p>\n'
            )
        ],
        [
            notify_markdown,
            'before\n\nafter\n',
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_multiple_newlines_get_truncated(markdown_function, expected):
    assert markdown_function(
        'before\n\n\n\n\n\nafter'
    ) == expected


@pytest.mark.parametrize('markdown_function', (
    notify_html_markdown, notify_markdown
))
def test_table(markdown_function):
    """
    Delete tables.  Note that supporting them would be very easy.  Both renderers use Mistune's "table"
    plugin.  To support tables, delete the overridden "table" method from the renderer.
    """

    assert markdown_function(
        'col | col\n'
        '----|----\n'
        'val | val\n'
    ).rstrip() == (
        ''
    )


@pytest.mark.parametrize(
    'markdown_function, link, expected',
    (
        [
            notify_html_markdown,
            'http://example.com',
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
                '<a style="word-wrap: break-word; color: #004795;" target="_blank" '
                'href="http://example.com">http://example.com</a>'
                '</p>\n'
            )
        ],
        [
            notify_html_markdown,
            """https://example.com"onclick="alert('hi')""",
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
                '<a style="word-wrap: break-word; color: #004795;" target="_blank" '
                'href="https://example.com%22onclick=%22alert(%27hi">'
                'https://example.com&quot;onclick=&quot;alert(\'hi'
                '</a>\')'
                '</p>\n'
            )
        ],
        [
            notify_markdown,
            'http://example.com',
            'http://example.com\n'
        ],
    ),
    ids=['html_link', 'html_link_js', 'markdown']
)
def test_autolink(markdown_function, link, expected):
    assert markdown_function(link) == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">'
            'variable called <code>thing</code></p>\n'
        ],
        [
            notify_markdown,
            'variable called `thing`\n',
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_codespan(markdown_function, expected):
    assert markdown_function('variable called `thing`') == expected


@pytest.mark.parametrize('markdown_function, expected', (
    [
        notify_html_markdown,
        '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; '
        'color: #323A45;">something <strong>important</strong></p>\n'
    ],
    [
        notify_markdown,
        'something **important**\n',
    ],
))
def test_double_emphasis(markdown_function, expected):
    assert markdown_function('something __important__') == expected


@pytest.mark.parametrize('markdown_function, expected', (
    [
        notify_html_markdown,
        '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; '
        'color: #323A45;">something <em>important</em></p>\n'
    ],
    [
        notify_markdown,
        'something *important*\n',
    ],
))
def test_emphasis(markdown_function, expected):
    assert markdown_function('something _important_') == expected


@pytest.mark.parametrize('markdown_function, expected', (
    [
        notify_html_markdown,
        '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; '
        'color: #323A45;">foo <em><strong>bar</strong></em></p>\n'
    ],
    [
        notify_markdown,
        'foo ***bar***\n',
    ],
))
def test_nested_emphasis(markdown_function, expected):
    """
    Note that this behavior has no correstpondence with Github markdown.  The expected
    output is simply what the renderer actually does.
    """

    assert markdown_function('foo ___bar___') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    [
        (notify_html_markdown, ''),
        (notify_markdown, '\n'),
    ],
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_image(markdown_function, expected):
    assert markdown_function('![alt text](http://example.com/image.png)') == expected


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; '
                'color: #323A45;">'
                '<a style="word-wrap: break-word; color: #004795;" '
                'target="_blank" href="http://example.com">Example</a>'
                '</p>\n'
            )
        ],
        [
            notify_markdown,
            'Example: http://example.com\n',
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_link(markdown_function, expected):
    assert markdown_function('[Example](http://example.com)') == expected


def test_link_with_title():
    assert notify_html_markdown('[Example](http://example.com "An example URL")') == (
        '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; '
        'color: #323A45;">'
        '<a style="word-wrap: break-word; color: #004795;" target="_blank" href="http://example.com" '
        'title="An example URL">'
        'Example'
        '</a>'
        '</p>\n'
    )


@pytest.mark.parametrize(
    'markdown_function, expected',
    (
        [
            notify_html_markdown,
            '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;"><del>Strike</del></p>\n'
        ],
        [
            notify_markdown,
            '\n\nStrike\n'
        ],
    ),
    ids=['notify_html_markdown', 'notify_markdown']
)
def test_strikethrough(markdown_function, expected):
    assert markdown_function('~~Strike~~') == expected


def test_footnotes():
    # Can’t work out how to test this
    pass


def test_sms_encode():
    assert sms_encode('aàá…') == 'aàa...'


@pytest.mark.parametrize('items, kwargs, expected_output', [
    ([1], {}, '‘1’'),
    ([1, 2], {}, '‘1’ and ‘2’'),
    ([1, 2, 3], {}, '‘1’, ‘2’ and ‘3’'),
    ([1, 2, 3], {'prefix': 'foo', 'prefix_plural': 'bar'}, 'bar ‘1’, ‘2’ and ‘3’'),
    ([1], {'prefix': 'foo', 'prefix_plural': 'bar'}, 'foo ‘1’'),
    ([1, 2, 3], {'before_each': 'a', 'after_each': 'b'}, 'a1b, a2b and a3b'),
    ([1, 2, 3], {'conjunction': 'foo'}, '‘1’, ‘2’ foo ‘3’'),
    (['&'], {'before_each': '<i>', 'after_each': '</i>'}, '<i>&amp;</i>'),
    ([1, 2, 3], {'before_each': '<i>', 'after_each': '</i>'}, '<i>1</i>, <i>2</i> and <i>3</i>'),
])
def test_formatted_list(items, kwargs, expected_output):
    assert formatted_list(items, **kwargs) == expected_output


def test_formatted_list_returns_markup():
    assert isinstance(formatted_list([0]), Markup)


def test_removing_dvla_markup():
    assert strip_dvla_markup(
        (
            'some words & some more <words>'
            '<cr><h1><h2><p><normal><op><np><bul><tab>'
            '<CR><H1><H2><P><NORMAL><OP><NP><BUL><TAB>'
            '<tAb>'
        )
    ) == 'some words & some more <words>'


def test_removing_pipes():
    assert strip_pipes('|a|b|c') == 'abc'


def test_bleach_doesnt_try_to_make_valid_html_before_cleaning():
    assert escape_html(
        "<to cancel daily cat facts reply 'cancel'>"
    ) == (
        "&lt;to cancel daily cat facts reply 'cancel'&gt;"
    )


@pytest.mark.parametrize('dirty, clean', [
    (
        'Hello ((name)) ,\n\nThis is a message',
        'Hello ((name)),\n\nThis is a message'
    ),
    (
        'Hello Jo ,\n\nThis is a message',
        'Hello Jo,\n\nThis is a message'
    ),
    (
        '\n   \t    , word',
        '\n, word',
    ),
])
def test_removing_whitespace_before_commas(dirty, clean):
    assert remove_whitespace_before_punctuation(dirty) == clean


@pytest.mark.parametrize('dirty, clean', [
    (
        'Hello ((name)) .\n\nThis is a message',
        'Hello ((name)).\n\nThis is a message'
    ),
    (
        'Hello Jo .\n\nThis is a message',
        'Hello Jo.\n\nThis is a message'
    ),
    (
        '\n   \t    . word',
        '\n. word',
    ),
])
def test_removing_whitespace_before_full_stops(dirty, clean):
    assert remove_whitespace_before_punctuation(dirty) == clean


@pytest.mark.parametrize('dumb, smart', [
    (
        """And I said, "what about breakfast at Tiffany's"?""",
        """And I said, “what about breakfast at Tiffany’s”?""",
    ),
    (
        """
            <a href="http://example.com?q='foo'">http://example.com?q='foo'</a>
        """,
        """
            <a href="http://example.com?q='foo'">http://example.com?q='foo'</a>
        """,
    ),
])
def test_smart_quotes(dumb, smart):
    assert make_quotes_smart(dumb) == smart


@pytest.mark.parametrize('nasty, nice', [
    (
        (
            'The en dash - always with spaces in running text when, as '
            'discussed in this section, indicating a parenthesis or '
            'pause - and the spaced em dash both have a certain '
            'technical advantage over the unspaced em dash. '
        ),
        (
            'The en dash \u2013 always with spaces in running text when, as '
            'discussed in this section, indicating a parenthesis or '
            'pause \u2013 and the spaced em dash both have a certain '
            'technical advantage over the unspaced em dash. '
        ),
    ),
    (
        'double -- dash',
        'double \u2013 dash',
    ),
    (
        'triple --- dash',
        'triple \u2013 dash',
    ),
    (
        'quadruple ---- dash',
        'quadruple ---- dash',
    ),
    (
        'em — dash',
        'em – dash',
    ),
    (
        'already\u0020–\u0020correct',  # \u0020 is a normal space character
        'already\u0020–\u0020correct',
    ),
    (
        '2004-2008',
        '2004-2008',  # no replacement
    ),
])
def test_en_dashes(nasty, nice):
    assert replace_hyphens_with_en_dashes(nasty) == nice


def test_unicode_dash_lookup():
    en_dash_replacement_sequence = '\u0020\u2013'
    hyphen = '-'
    en_dash = '–'
    space = ' '
    non_breaking_space = ' '
    assert en_dash_replacement_sequence == space + en_dash
    assert non_breaking_space not in en_dash_replacement_sequence
    assert hyphen not in en_dash_replacement_sequence


@pytest.mark.parametrize('markup, expected_fixed', [
    (
        'a',
        'a',
    ),
    (
        'before<p><cr><p><cr>after',
        'before<p><cr>after',
    ),
    (
        'before<cr><cr><np>after',
        'before<cr><np>after',
    ),
    (
        'before{}<np>after'.format('<cr>' * 4),
        'before{}<np>after'.format('<cr>' * 3),
    ),
])
def test_tweaking_dvla_list_markup(markup, expected_fixed):
    assert tweak_dvla_list_markup(markup) == expected_fixed


def test_make_list_from_linebreaks():
    assert nl2li(
        'a\n'
        'b\n'
        'c\n'
    ) == (
        '<ul>'
        '<li>a</li>'
        '<li>b</li>'
        '<li>c</li>'
        '</ul>'
    )


@pytest.mark.parametrize('value', [
    'bar',
    ' bar ',
    """
        \t    bar
    """,
    ' \u180E\u200B \u200C bar \u200D \u2060\uFEFF ',
])
def test_strip_whitespace(value):
    assert strip_whitespace(value) == 'bar'


@pytest.mark.parametrize('value', [
    'notifications-email',
    '  \tnotifications-email \x0c ',
    '\rn\u200Coti\u200Dfi\u200Bcati\u2060ons-\u180Eemai\uFEFFl\uFEFF',
])
def test_strip_and_remove_obscure_whitespace(value):
    assert strip_and_remove_obscure_whitespace(value) == 'notifications-email'


def test_strip_and_remove_obscure_whitespace_only_removes_normal_whitespace_from_ends():
    sentence = '   words \n over multiple lines with \ttabs\t   '
    assert strip_and_remove_obscure_whitespace(sentence) == 'words \n over multiple lines with \ttabs'


def test_remove_smart_quotes_from_email_addresses():
    assert remove_smart_quotes_from_email_addresses("""
        line one’s quote
        first.o’last@example.com is someone’s email address
        line ‘three’
    """) == ("""
        line one’s quote
        first.o'last@example.com is someone’s email address
        line ‘three’
    """)


def test_strip_unsupported_characters():
    assert strip_unsupported_characters("line one\u2028line two") == ("line oneline two")


def test_normalise_whitespace():
    assert normalise_whitespace('\u200C Your tax   is\ndue\n\n') == 'Your tax is due'


@pytest.mark.parametrize(
    'actual, expected',
    [
        (
            '1.one\n2.two\n3.three',
            '1. one\n2. two\n3. three',
        ),
        (
            '-one\n   -two\n-three',
            '- one\n   - two\n- three',
        ),
        (
            '+one\n   +two\n+three',
            '- one\n   - two\n- three',
        ),
        (
            '*one\n   *two\n*three',
            '- one\n   - two\n- three',
        ),
        (
            '•one\n   •two\n•three',
            '- one\n   - two\n- three',
        ),
        # Next 2 tests: Shouldn't misinterpret a thematic break as a list item
        (
            '***one\n   *two\n*three',
            '***one\n   - two\n- three',
        ),
        (
            '-one\n   ---two\n-three',
            '- one\n   ---two\n- three',
        ),
        (
            '# This is Heading 1\n'
            '## This is heading 2\n'
            '### This is heading 3\n'
            '\n'
            '__This has been emboldened__\n'
            '\n'
            '- this is a bullet list\n'
            '- list list list\n'
            '\n'
            'Testing personalisation, ((name)).\n',
            '# This is Heading 1\n'
            '## This is heading 2\n'
            '### This is heading 3\n'
            '\n'
            '__This has been emboldened__\n'
            '\n'
            '- this is a bullet list\n'
            '- list list list\n'
            '\n'
            'Testing personalisation, ((name)).\n',
        ),
    ]
)
def test_insert_list_spaces(actual, expected):
    assert insert_list_spaces(actual) == expected

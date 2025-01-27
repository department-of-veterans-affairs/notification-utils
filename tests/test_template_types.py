from time import process_time
from unittest import mock

import pytest
from markupsafe import Markup

from notifications_utils.formatters import (
    BLOCK_QUOTE_STYLE,
    LINK_STYLE,
    LIST_ITEM_STYLE,
    ORDERED_LIST_STYLE,
    PARAGRAPH_STYLE,
    UNORDERED_LIST_STYLE
)
from notifications_utils.template import (
    Template,
    HTMLEmailTemplate,
    PlainTextEmailTemplate,
    SMSMessageTemplate,
    SMSPreviewTemplate,
    WithSubjectTemplate,
    EmailPreviewTemplate,
    get_html_email_body,
)


def test_pass_through_renderer():
    message = '''
        the
        quick brown
        fox
    '''
    assert str(Template({'content': message})) == message


@pytest.mark.parametrize(
    'content, values, expected',
    [
        (
            'line one\nline two with ((name))\n\nnew paragraph',
            {'name': 'bob'},
            (
                f'<p style="{PARAGRAPH_STYLE}">line one<br />\nline two with bob</p>\n'
                f'<p style="{PARAGRAPH_STYLE}">new paragraph</p>\n'
            ),
        ),
        (
            '>>[action](https://example.com/foo?a=b)',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}"><a href="https://example.com/foo?a=b">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>action</b></a></p>\n'
            )
        ),
        (
            (
                '\n# foo\n'
                '\n## Bar\n'
                '\nThe quick ((color)) fox '
                '\n>>[the action_link-of doom](https://example.com)'
            ),
            {'color': 'brown'},
            (
                '<h1 style="Margin: 0 0 20px 0; padding: 0; font-size: 32px; line-height: 35px; font-weight: bold; '
                'color: #323A45;">foo</h1>\n'
                '<h2 style="Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #323A45; '
                'font-size: 24px; font-weight: bold; font-family: Helvetica, Arial, sans-serif;">Bar</h2>\n'
                f'<p style="{PARAGRAPH_STYLE}">The quick brown fox</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="https://example.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>the action_link-of doom</b></a></p>\n'
            ),
        ),
        (
            'text before link\n\n>>[great link](http://example.com)\n\ntext after link',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}">text before link</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="http://example.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>great link</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">text after link</p>\n'
            )
        ),
        (
            'action link: &gt;&gt;[Example](http://example.com)\nanother link: [test](https://example2.com)',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}">action link:</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="http://example.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>Example</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">'
                f'another link: <a style="{LINK_STYLE}" target="_blank" href="https://example2.com">test</a></p>\n'
            )
        ),
        (
            'action link: &gt;&gt;[grin](http://example.com) another action link: >>[test](https://example2.com)',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}">action link:</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="http://example.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>grin</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">another action link:</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="https://example2.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>test</b></a></p>\n'
            )
        ),
        (
            'text before && link &gt;&gt;[Example](http://example.com) text after & link',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}">text before &amp;&amp; link</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="http://example.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>Example</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">text after &amp; link</p>\n'
            )
        ),
        (
            'text before >> link &gt;&gt;[great action](http://example.com) text after >>link',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}">text before &gt;&gt; link</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="http://example.com">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>great action</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">text after &gt;&gt;link</p>\n'
            )
        ),
        (
            'text >> then [item] and (things) then >>[action](link)',
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}">text &gt;&gt; then [item] and (things) then</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="link">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>action</b></a></p>\n'
            )
        ),
        (
            (
                '>>[action link](#)'
                '\n\ntesting the new >>[action link](#) thingy...'
                '\n\n>>[click me](#)! Text with a [regular link](#)'
            ),
            {},
            (
                f'<p style="{PARAGRAPH_STYLE}"><a href="#">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>action link</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">testing the new</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="#">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>action link</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">thingy...</p>\n'
                f'<p style="{PARAGRAPH_STYLE}"><a href="#">'
                '<img alt="call to action img" '
                'src="https://dev-va-gov-assets.s3-us-gov-west-1.amazonaws.com/img/vanotify-action-link.png" '
                'style="vertical-align: middle;"> <b>click me</b></a></p>\n'
                f'<p style="{PARAGRAPH_STYLE}">! Text with a '
                '<a style="word-wrap: break-word; color: #004795;" target="_blank" href="#">regular link</a></p>\n'
            )
        )
    ],
    ids=[
        'no link, newline in text',
        'action link',
        'action link with text',
        'action link on newline',
        'action and regular link',
        'action links x2',
        'action link and text with "&&"',
        'action link and text with ">>"',
        'action link after parts',
        'two of the same action link',
    ]
)
def test_get_html_email_body_with_action_links(content, values, expected):
    assert get_html_email_body(content, values) == expected


@pytest.mark.parametrize(
    'content, expected',
    [
        (
            'normal placeholder formatting: ((foo))',
            (
                f'<p style="{PARAGRAPH_STYLE}">normal placeholder formatting: <span class=\'placeholder\'><mark>((foo))'
                '</mark></span></p>\n'
            ),
        ),
        (
            'regular markdown link: [link text](#)',
            (
                f'<p style="{PARAGRAPH_STYLE}">regular markdown link: '
                f'<a style="{LINK_STYLE}" target="_blank" href="#">link text</a></p>\n'
            ),
        ),
        (
            'placeholder in link text, without placeholder in link: [link ((foo))](https://test.com/)',
            (
                f'<p style="{PARAGRAPH_STYLE}">placeholder in link text, without placeholder in link: '
                f'<a style="{LINK_STYLE}" target="_blank" href="https://test.com/">link '
                '<span class=\'placeholder\'><mark>((foo))</mark></span></a></p>\n'
            ),
        ),
        (
            'no format within link, placeholder at end: [link text](https://test.com/((foo)))',
            (
                f'<p style="{PARAGRAPH_STYLE}">no format within link, placeholder at end: '
                f'<a style="{LINK_STYLE}" target="_blank" href="https://test.com/((foo))">link text</a></p>\n'
            )
        ),
        (
            'no format within link, placeholder in middle: [link text](https://test.com/((foo))?xyz=123)',
            (
                f'<p style="{PARAGRAPH_STYLE}">no format within link, placeholder in middle: '
                f'<a style="{LINK_STYLE}" target="_blank" href="https://test.com/((foo))?xyz=123">link text</a></p>\n'
            )
        ),
        (
            'no format in link, with only placeholder: [link text](((foo)))',
            (
                f'<p style="{PARAGRAPH_STYLE}">no format in link, with only placeholder: '
                f'<a style="{LINK_STYLE}" target="_blank" href="((foo))">link text</a></p>\n'
            )
        ),
        (
            'no format within link, multiple placeholders: [link text](https://test.com/((foo))?xyz=((bar)))',
            (
                f'<p style="{PARAGRAPH_STYLE}">no format within link, multiple placeholders: '
                f'<a style="{LINK_STYLE}" target="_blank" href="https://test.com/((foo))?xyz=((bar))">'
                'link text</a></p>\n'
            )
        ),
    ],
    ids=[
        'formatting with placeholder',
        'no formatting with only markdown link',
        'formatting with placeholder in markdown link text',
        'formatting with placeholder in markdown link url',
        'formatting with placeholder in markdown link url and text around placeholder',
        'formatting when placeholder is markdown link url',
        'formatting with multiple placeholders in markdown link'
    ]
)
def test_get_html_email_body_preview_with_placeholder_in_markdown_link(content, expected):
    assert get_html_email_body(content, template_values={}, preview_mode=True) == expected


def test_html_email_inserts_body():
    content = 'the <em>quick</em> brown fox'
    assert content in str(HTMLEmailTemplate({'content': content, 'subject': ''}))


@pytest.mark.parametrize(
    "content, ga_pixel_url, params", [
        ('some text', 'pix-url', None),
        ('some text containing ((param1))', 'pix-url', {'param1': 'value1'})
    ]
)
def test_html_email_inserts_gapixel_img_when_ga_pixel_url_is_present(content, ga_pixel_url, params):
    email_body = HTMLEmailTemplate(
        {'content': content, 'subject': ''},
        values=params,
        ga_pixel_url=ga_pixel_url
    )
    assert '<img id="ga_pixel_url" src="{}'.format(ga_pixel_url) in str(email_body)


@pytest.mark.parametrize(
    "content, ga4_open_email_event_url, params", [
        ('some text', 'pix-url', None),
        ('some text containing ((param1))', 'pix-url', {'param1': 'value1'})
    ]
)
def test_html_email_inserts_img_when_ga4_open_email_event_url_is_present(content, ga4_open_email_event_url, params):
    email_body = HTMLEmailTemplate(
        {'content': content, 'subject': ''},
        values=params,
        ga4_open_email_event_url=ga4_open_email_event_url
    )
    assert '<img id="ga4_open_email_event_url" src="{}'.format(ga4_open_email_event_url) in str(email_body)


@pytest.mark.parametrize(
    "content, params", [
        ('some text', None),
        ('some text containing ((param1))', {'param1': 'value1'})
    ]
)
def test_html_email_no_gapixel_img_when_ga_pixel_url_is_not_present(content, params):
    email_body = HTMLEmailTemplate(
        {'content': content, 'subject': ''},
        values=params,
        ga_pixel_url=None
    )
    assert '<img id="ga_pixel_url" src=' not in str(email_body)


@pytest.mark.parametrize(
    "content", ('DOCTYPE', 'html', 'body', 'hello world')
)
def test_default_template(content):
    assert content in str(HTMLEmailTemplate({'content': 'hello world', 'subject': ''}))


@pytest.mark.parametrize(
    "show_banner", (True, False)
)
def test_default_banner(show_banner):
    email = HTMLEmailTemplate({'content': 'hello world', 'subject': ''})
    email.default_banner = show_banner
    if show_banner:
        assert "vanotify-header-logo.png" in str(email)
    else:
        assert "vanotify-header-logo.png" not in str(email)


def test_brand_banner_shows():
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        brand_banner=True,
        default_banner=False
    ))
    assert (
        '<td width="10" height="10" valign="middle"></td>'
    ) not in email
    assert (
        'role="presentation" width="100%" style="border-collapse: collapse;min-width: 100%;width: 100% !important;"'
    ) in email


@pytest.mark.parametrize(
    "brand_logo, brand_text, brand_colour",
    [
        ('http://example.com/image.png', 'Example', 'red'),
        ('http://example.com/image.png', 'Example', '#f00'),
        ('http://example.com/image.png', 'Example', None),
        ('http://example.com/image.png', '', '#f00'),
        (None, 'Example', '#f00')
    ]
)
def test_brand_data_shows(brand_logo, brand_text, brand_colour):
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        brand_banner=True,
        default_banner=False,
        brand_logo=brand_logo,
        brand_text=brand_text,
        brand_colour=brand_colour
    ))

    assert 'GOV.UK' not in email
    if brand_logo:
        assert brand_logo in email
    if brand_text:
        assert brand_text in email
    if brand_colour:
        assert 'bgcolor="{}"'.format(brand_colour) in email


def test_brand_log_has_no_alt_text_when_brand_text_is_present():
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        default_banner=True,
        brand_logo='http://example.com/image.png',
        brand_text='Example',
        brand_banner=True,
        brand_name='Notify Logo'
    ))
    assert 'alt="U.S. Department of Veterans Affairs"' in email
    assert 'alt=" "' in email
    assert 'alt="Notify Logo"' not in email


def test_brand_logo_has_alt_text_when_no_brand_text():
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        default_banner=True,
        brand_logo='http://example.com/image.png',
        brand_text=None,
        brand_banner=True,
        brand_name='Notify Logo'
    ))
    assert 'alt="U.S. Department of Veterans Affairs"' in email
    assert 'alt="Notify Logo"' in email


@pytest.mark.parametrize('brand_banner, brand_text, expected_alt_text', [
    (True, None, 'alt="Notify Logo"'),
    (True, 'Example', 'alt=" "'),
    (False, 'Example', 'alt=" "'),
    (False, None, 'alt="Notify Logo"'),
])
def test_alt_text_with_no_default_banner(brand_banner, brand_text, expected_alt_text):
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        default_banner=False,
        brand_logo='http://example.com/image.png',
        brand_text=brand_text,
        brand_banner=brand_banner,
        brand_name='Notify Logo'
    ))

    assert expected_alt_text in email


@pytest.mark.parametrize(
    "complete_html", (True, False)
)
@pytest.mark.parametrize(
    "branding_should_be_present, brand_logo, brand_text, brand_colour",
    [
        (True, 'http://example.com/image.png', 'Example', '#f00'),
        (True, 'http://example.com/image.png', 'Example', None),
        (True, 'http://example.com/image.png', '', None),
        (False, None, 'Example', '#f00'),
        (False, 'http://example.com/image.png', None, '#f00')
    ]
)
@pytest.mark.parametrize(
    "content", ('DOCTYPE', 'html', 'body')
)
def test_complete_html(complete_html, branding_should_be_present, brand_logo, brand_text, brand_colour, content):

    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        complete_html=complete_html,
        brand_logo=brand_logo,
        brand_text=brand_text,
        brand_colour=brand_colour,
    ))

    if complete_html:
        assert content in email
    else:
        assert content not in email

    if branding_should_be_present:
        assert brand_logo in email
        assert brand_text in email

        if brand_colour:
            assert brand_colour in email
            assert '##' not in email


def test_preheader_is_at_start_of_html_emails():
    assert (
        '<body style="mso-line-height-rule: exactly;font-family: Helvetica, Arial, sans-serif;'
        'font-size: 16px;Margin: 0;color:#323A45;">\n'
        '\n'
        '<span style="display: none;font-size: 1px;color: #fff; max-height: 0;">content…</span>'
    ) in str(HTMLEmailTemplate({'content': 'content', 'subject': 'subject'}))


@pytest.mark.parametrize(
    'content, values, expected_preheader',
    [
        (
            (
                'Hello (( name ))\n'
                '\n'
                '# This - is a "heading"\n'
                '\n'
                'My favourite websites\' URLs are:\n'
                '- va.gov\n'
                '- https://www.example.com\n'
            ),
            {'name': 'Jo'},
            'Hello Jo This – is a “heading” My favourite websites’ URLs are: • va.gov • https://www.example.com',
        ),
        (
            (
                '[Markdown link](https://www.example.com)\n'
            ),
            {},
            'Markdown link',
        ),
        (
            (
                '>>[action link](https://www.example.com)\n'
            ),
            {},
            'action link',
        ),
        (
            """
                Lorem Ipsum is simply dummy text of the printing and
                typesetting industry.

                Lorem Ipsum has been the industry’s standard dummy text
                ever since the 1500s, when an unknown printer took a galley
                of type and scrambled it to make a type specimen book.

                Lorem Ipsum is simply dummy text of the printing and
                typesetting industry.

                Lorem Ipsum has been the industry’s standard dummy text
                ever since the 1500s, when an unknown printer took a galley
                of type and scrambled it to make a type specimen book.
            """,
            {},
            (
                'Lorem Ipsum is simply dummy text of the printing and '
                'typesetting industry. Lorem Ipsum has been the industry’s '
                'standard dummy text ever since the 1500s, when an unknown '
                'printer took a galley of type and scrambled it to make a '
                'type specimen book. Lorem Ipsu'
            ),
        ),
        (
            'short email',
            {},
            'short email',
        ),
    ],
    ids=['1', '2', '3', '4', '5']
)
def test_content_of_preheader_in_html_emails(
    content,
    values,
    expected_preheader,
):
    assert HTMLEmailTemplate(
        {'content': content, 'subject': 'subject'},
        values
    ).preheader == expected_preheader


def test_markdown_in_templates():
    str(HTMLEmailTemplate(
        {
            "content": (
                'the quick ((colour)) ((animal))\n'
                '\n'
                'jumped over the lazy dog'
            ),
            'subject': 'animal story'
        },
        {'animal': 'fox', 'colour': 'brown'},
    )) == 'the quick brown fox\n\njumped over the lazy dog\n'


@pytest.mark.parametrize(
    'template_class',
    [
        HTMLEmailTemplate,
        EmailPreviewTemplate,
        SMSPreviewTemplate,
    ]
)
@pytest.mark.parametrize(
    "url, url_with_entities_replaced",
    [
        ("http://example.com", "http://example.com"),
        ("http://www.gov.uk/", "http://www.gov.uk/"),
        ("https://www.gov.uk/", "https://www.gov.uk/"),
        ("http://service.gov.uk", "http://service.gov.uk"),
        (
            "http://service.gov.uk/blah.ext?q=a%20b%20c&order=desc#fragment",
            "http://service.gov.uk/blah.ext?q=a%20b%20c&amp;order=desc#fragment",
        ),
    ]
)
def test_makes_links_out_of_URLs(template_class, url, url_with_entities_replaced):
    assert '<a style="{}" target="_blank" href="{}">{}</a>'.format(
        LINK_STYLE, url_with_entities_replaced, url_with_entities_replaced
    ) in str(template_class({'content': url, 'subject': ''}))


@pytest.mark.parametrize(
    'content, html_snippet',
    (
        (
            (
                'You’ve been invited to a service. Click this link:\n'
                'https://service.example.com/accept_invite/a1b2c3d4\n'
                '\n'
                'Thanks\n'
            ),
            (
                '<a style="word-wrap: break-word; color: #004795;" target="_blank"'
                ' href="https://service.example.com/accept_invite/a1b2c3d4">'
                'https://service.example.com/accept_invite/a1b2c3d4'
                '</a>'
            ),
        ),
        (
            (
                'https://service.example.com/accept_invite/?a=b&c=d&'
            ),
            (
                '<a style="word-wrap: break-word; color: #004795;" target="_blank"'
                ' href="https://service.example.com/accept_invite/?a=b&amp;c=d&amp;">'
                'https://service.example.com/accept_invite/?a=b&amp;c=d&amp;'
                '</a>'
            ),
        ),
    ),
    ids=['no_url_params', 'with_url_params']
)
def test_HTML_template_has_URLs_replaced_with_links(content, html_snippet):
    assert html_snippet in str(HTMLEmailTemplate({'content': content, 'subject': ''}))


def test_stripping_of_unsupported_characters_in_email_templates():
    template_content = "line one\u2028line two"
    expected = "line oneline two"
    assert expected in str(PlainTextEmailTemplate({'content': template_content, 'subject': ''}))
    assert expected in str(HTMLEmailTemplate({'content': template_content, 'subject': ''}))


@pytest.mark.parametrize(
    "template_class, prefix, body, expected",
    [
        (SMSMessageTemplate, 'a', 'b', 'a: b'),
        (SMSMessageTemplate, None, 'b', 'b'),
        (SMSMessageTemplate, '<em>ht&ml</em>', 'b', '<em>ht&ml</em>: b'),
        (SMSPreviewTemplate, 'a', 'b', '\n\n<div class="sms-message-wrapper">\n  a: b\n</div>'),
        (SMSPreviewTemplate, None, 'b', '\n\n<div class="sms-message-wrapper">\n  b\n</div>'),
        (
            SMSPreviewTemplate,
            '<em>ht&ml</em>',
            'b',
            '\n\n<div class="sms-message-wrapper">\n  &lt;em&gt;ht&amp;ml&lt;/em&gt;: b\n</div>',
        ),
    ],
    ids=['message_a', 'message_none', 'message_html', 'preview_a', 'preview_none', 'preview_html']
)
def test_sms_templates_add_prefix(template_class, prefix, body, expected):
    template = template_class({'content': body})
    template.prefix = prefix
    template.sender = None
    assert str(template) == expected


@pytest.mark.parametrize(
    "template_class, show_prefix, prefix, body, sender, expected",
    [
        (SMSMessageTemplate, False, "a", "b", "c", 'b'),
        (SMSMessageTemplate, True, "a", "b", None, 'a: b'),
        (SMSMessageTemplate, True, "a", "b", False, 'a: b'),
        (SMSPreviewTemplate, False, "a", "b", "c", '\n\n<div class="sms-message-wrapper">\n  b\n</div>'),
        (SMSPreviewTemplate, True, "a", "b", None, '\n\n<div class="sms-message-wrapper">\n  a: b\n</div>'),
        (SMSPreviewTemplate, True, "a", "b", False, '\n\n<div class="sms-message-wrapper">\n  a: b\n</div>'),
    ]
)
def test_sms_message_adds_prefix_only_if_asked_to(
    template_class,
    show_prefix,
    prefix,
    body,
    sender,
    expected,
):
    template = template_class(
        {'content': body},
        prefix=prefix,
        show_prefix=show_prefix,
        sender=sender,
    )
    assert str(template) == expected


@pytest.mark.parametrize('content_to_look_for', [
    'GOVUK', 'sms-message-sender'
])
@pytest.mark.parametrize("show_sender", [
    True,
    pytest.param(False, marks=pytest.mark.xfail),
])
def test_sms_message_preview_shows_sender(
    show_sender,
    content_to_look_for,
):
    assert content_to_look_for in str(SMSPreviewTemplate(
        {'content': 'foo'},
        sender='GOVUK',
        show_sender=show_sender,
    ))


def test_sms_message_preview_hides_sender_by_default():
    assert SMSPreviewTemplate({'content': 'foo'}).show_sender is False


@mock.patch('notifications_utils.template.sms_encode', return_value='downgraded')
@pytest.mark.parametrize(
    'template_class', [SMSMessageTemplate, SMSPreviewTemplate]
)
def test_sms_messages_downgrade_non_sms(mock_sms_encode, template_class):
    template = str(template_class({'content': 'Message'}, prefix='Service name'))
    assert 'downgraded' in str(template)
    mock_sms_encode.assert_called_once_with('Service name: Message')


@mock.patch('notifications_utils.template.sms_encode', return_value='downgraded')
def test_sms_messages_dont_downgrade_non_sms_if_setting_is_false(mock_sms_encode):
    template = str(SMSPreviewTemplate(
        {'content': '😎'},
        prefix='👉',
        downgrade_non_sms_characters=False,
    ))
    assert '👉: 😎' in str(template)
    assert mock_sms_encode.called is False


@mock.patch('notifications_utils.template.nl2br', return_value='')
def test_sms_preview_adds_newlines(nl2br):
    content = "the\nquick\n\nbrown fox"
    str(SMSPreviewTemplate({'content': content}))
    nl2br.assert_called_once_with(content)


@pytest.mark.parametrize('content', [
    (  # Unix-style
        'one newline\n'
        'two newlines\n'
        '\n'
        'end'
    ),
    (  # Windows-style
        'one newline\r\n'
        'two newlines\r\n'
        '\r\n'
        'end'
    ),
    (  # Mac Classic style
        'one newline\r'
        'two newlines\r'
        '\r'
        'end'
    ),
    (  # A mess
        '\t\t\n\r one newline\xa0\n'
        'two newlines\r'
        '\r\n'
        'end\n\n  \r \n \t '
    ),
])
def test_sms_message_normalises_newlines(content):
    assert repr(str(SMSMessageTemplate({'content': content}))) == repr(
        'one newline\n'
        'two newlines\n'
        '\n'
        'end'
    )


def test_sets_subject():
    assert WithSubjectTemplate({"content": '', 'subject': 'Your tax is due'}).subject == 'Your tax is due'


def test_subject_line_gets_applied_to_correct_template_types():
    for cls in [
        EmailPreviewTemplate,
        HTMLEmailTemplate,
        PlainTextEmailTemplate,
    ]:
        assert issubclass(cls, WithSubjectTemplate)
    for cls in [
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ]:
        assert not issubclass(cls, WithSubjectTemplate)


def test_subject_line_gets_replaced():
    template = WithSubjectTemplate({"content": '', 'subject': '((name))'})
    assert template.subject == Markup("<span class='placeholder'>((name))</span>")
    template.values = {'name': 'Jo'}
    assert template.subject == 'Jo'


@pytest.mark.parametrize('template_class, extra_args, expected_field_calls', [
    (Template, {}, [
        mock.call('content', {}, html='escape', redact_missing_personalisation=False),
    ]),
    (WithSubjectTemplate, {}, [
        mock.call('content', {}, html='passthrough', redact_missing_personalisation=False, markdown_lists=True),
    ]),
    (PlainTextEmailTemplate, {}, [
        mock.call('content', {}, html='passthrough', markdown_lists=True)
    ]),
    (HTMLEmailTemplate, {}, [
        mock.call('content', {}, html='passthrough', markdown_lists=True,
                  redact_missing_personalisation=False, preview_mode=False),
        mock.call('content', {}, html='escape', markdown_lists=True),
    ]),
    (EmailPreviewTemplate, {}, [
        mock.call('content', {}, preview_mode=False, html='passthrough', markdown_lists=True,
                  redact_missing_personalisation=False),
        mock.call('subject', {}, html='escape', redact_missing_personalisation=False),
        mock.call('((email address))', {}, with_brackets=False),
    ]),
    (SMSMessageTemplate, {}, [
        mock.call('content', {}, html='passthrough'),
    ]),
    (SMSPreviewTemplate, {}, [
        mock.call('content', {}, html='escape', redact_missing_personalisation=False),
        mock.call('((phone number))', {}, with_brackets=False, html='escape'),
    ]),
    (Template, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, html='escape', redact_missing_personalisation=True),
    ]),
    (WithSubjectTemplate, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, html='passthrough', redact_missing_personalisation=True, markdown_lists=True),
    ]),
    (EmailPreviewTemplate, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, preview_mode=False, html='passthrough', markdown_lists=True,
                  redact_missing_personalisation=True),
        mock.call('subject', {}, html='escape', redact_missing_personalisation=True),
        mock.call('((email address))', {}, with_brackets=False),
    ]),
    (SMSPreviewTemplate, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, html='escape', redact_missing_personalisation=True),
        mock.call('((phone number))', {}, with_brackets=False, html='escape'),
    ]),
])
@mock.patch('notifications_utils.template.Field.__init__', return_value=None)
@mock.patch('notifications_utils.template.Field.__str__', return_value='1\n2\n3\n4\n5\n6\n7\n8')
def test_templates_handle_html_and_redacting(
    mock_field_str,
    mock_field_init,
    template_class,
    extra_args,
    expected_field_calls,
):
    assert str(template_class({'content': 'content', 'subject': 'subject'}, **extra_args))
    assert mock_field_init.call_args_list == expected_field_calls
    mock_field_str.assert_called()


@pytest.mark.parametrize(
    'template_class',
    [
        PlainTextEmailTemplate,
        HTMLEmailTemplate,
        EmailPreviewTemplate,
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ],
)
def test_templates_remove_whitespace_before_punctuation(template_class):
    template = template_class({'content': 'content  \t\t .', 'subject': 'subject\t \t,'})

    assert 'content.' in str(template)

    if hasattr(template, 'subject'):
        assert template.subject == 'subject,'


@pytest.mark.parametrize('content', (
    "first.o'last@example.com",
    "first.o’last@example.com",
))
@pytest.mark.parametrize('template_class', (
    HTMLEmailTemplate,
    PlainTextEmailTemplate,
    EmailPreviewTemplate,
))
def test_no_smart_quotes_in_email_addresses(template_class, content):
    template = template_class({
        'content': content,
        'subject': content,
    })
    assert "first.o'last@example.com" in str(template)
    assert template.subject == "first.o'last@example.com"


def test_smart_quotes_removed_from_long_template_in_under_a_second():
    long_string = 'a' * 100000
    template = PlainTextEmailTemplate({'content': long_string, 'subject': ''})

    start_time = process_time()

    str(template)

    assert process_time() - start_time < 1


@pytest.mark.parametrize('template_instance, expected_placeholders', [
    (
        SMSMessageTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content'],
    ),
    (
        SMSPreviewTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content'],
    ),
    (
        PlainTextEmailTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content', 'subject'],
    ),
    (
        HTMLEmailTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content', 'subject'],
    ),
    (
        EmailPreviewTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content', 'subject'],
    ),
])
def test_templates_extract_placeholders(
    template_instance,
    expected_placeholders,
):
    assert template_instance.placeholder_names == set(expected_placeholders)


@pytest.mark.parametrize('extra_args', [
    {
        'from_name': 'Example service'
    },
    {
        'from_name': 'Example service',
        'from_address': 'test@example.com',
    },
    pytest.param({}, marks=pytest.mark.xfail),
])
def test_email_preview_shows_from_name(extra_args):
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        **extra_args
    )
    assert '<th>[From]</th>' in str(template)
    assert 'Example service' in str(template)
    assert 'test@example.com' not in str(template)


def test_email_preview_escapes_html_in_from_name():
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        from_name='<script>alert("")</script>',
        from_address='test@example.com',
    )
    assert '<script>' not in str(template)
    assert '&lt;script&gt;alert("")&lt;/script&gt;' in str(template)


@pytest.mark.parametrize('extra_args', [
    {
        'reply_to': 'test@example.com'
    },
    pytest.param({}, marks=pytest.mark.xfail),
])
def test_email_preview_shows_reply_to_address(extra_args):
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        **extra_args
    )
    assert '<th>[Reply to]</th>' in str(template)
    assert 'test@example.com' in str(template)


@pytest.mark.parametrize('template_values, expected_content', [
    (
        {},
        '<span class=\'placeholder-no-brackets\'>email address</span>'
    ),
    (
        {'email address': 'test@example.com'},
        'test@example.com'
    ),
])
def test_email_preview_shows_recipient_address(
    template_values,
    expected_content,
):
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        template_values,
    )
    assert expected_content in str(template)


dvla_file_spec = [
    {
        'Field number': '1',
        'Field name': 'OTT',
        'Mandatory': 'Y',
        'Data type': 'N3',
        'Comment': """
            Current assumption is a single OTT for Notify = 140
            141 has also been reserved for future use
        """,
        'Example': '140',
    },
    {
        'Field number': '2',
        'Field name': 'ORG-ID',
        'Mandatory': 'Y',
        'Data type': 'N3',
        'Comment': 'Unique identifier for the sending organisation',
        'Example': '500',
    },
    {
        'Field number': '3',
        'Field name': 'ORG-NOTIFICATION-TYPE',
        'Mandatory': 'Y',
        'Data type': 'N3',
        'Comment': """
            Identifies the specific letter type for this organisation
        """,
        'Example': '001',
    },
    {
        'Field number': '4',
        'Field name': 'ORG-NAME',
        'Mandatory': 'Y',
        'Data type': 'A90',
        'Comment': """
            Free text organisation name which appears under the
            crest in large font

            Not used by Notify
        """,
        'Example': '',
    },
    {
        'Field number': '5',
        'Field name': 'NOTIFICATION-ID',
        'Mandatory': 'Y',
        'Data type': 'A15',
        'Comment': """
            Unique identifier for each notification consisting of
            the current date and a numeric counter that resets each
            day.  Supports a maximum of 10 million notification
            events per day. Format:
                CCYYMMDDNNNNNNN
            Where:
                CCYY = Current year
                MMDD = Current month and year (zero padded)
                NNNNNNN = Daily counter (zero padded to 7 digits)
        """,
        'Example': 'reference',
    },
    {
        'Field number': '6',
        'Field name': 'NOTIFICATION-DATE',
        'Mandatory': 'Y',
        'Data type': 'A8',
        'Comment': """
            The date that will be shown on the notification Provided
            in format': 'DDMMYYYY This will be formatted to a long
            date format by the composition process

            Not used by Notify

            Given example was: 29042016
        """,
        'Example': '',
    },
    {
        'Field number': '7',
        'Field name': 'CUSTOMER-REFERENCE',
        'Mandatory': '',
        'Data type': 'A30',
        'Comment': """
            Full text of customer\'s reference

            Not implemented by Notify yet.

            Given example was:
                Our ref: 1234-5678
        """,
        'Example': '',
    },
    {
        'Field number': '8',
        'Field name': 'ADDITIONAL-LINE-1',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': """
            In the example templates this information appears in the
            footer in a small font.   These lines are free text,
            they may contain an address, e.g. of originating
            department, E9 but this will not be validated or used as
            a return address.
        """,
        'Example': 'The Pension Service',
    },
    {
        'Field number': '9',
        'Field name': 'ADDITIONAL-LINE-2',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Mail Handling Site A',
    },
    {
        'Field number': '10',
        'Field name': 'ADDITIONAL-LINE-3',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Wolverhampton  WV9 1LU',
    },
    {
        'Field number': '11',
        'Field name': 'ADDITIONAL-LINE-4',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': 'Deliberate blank line',
        'Example': '',
    },
    {
        'Field number': '12',
        'Field name': 'ADDITIONAL-LINE-5',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Telephone: 0845 300 0168',
    },
    {
        'Field number': '13',
        'Field name': 'ADDITIONAL-LINE-6',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Email: fpc.customercare@dwp.gsi.gov.uk',
    },
    {
        'Field number': '14',
        'Field name': 'ADDITIONAL-LINE-7',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Monday - Friday  8am - 6pm',
    },
    {
        'Field number': '15',
        'Field name': 'ADDITIONAL-LINE-8',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'www.gov.uk',
    },
    {
        'Field number': '16',
        'Field name': 'ADDITIONAL-LINE-9',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '17',
        'Field name': 'ADDITIONAL-LINE-10',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '18',
        'Field name': 'TO-NAME-1',
        'Mandatory': 'Y',
        'Data type': 'A60',
        'Comment': """
            Recipient full name includes title Must be present -
            validated by Notify
        """,
        'Example': 'Mr Henry Hadlow',
    },
    {
        'Field number': '19',
        'Field name': 'TO-NAME-2',
        'Mandatory': '',
        'Data type': 'A40',
        'Comment': """
            Additional name or title line

            Not able to pass this through at the moment

            Given example was: Managing Director
        """,
        'Example': '',
    },
    {
        'Field number': '20',
        'Field name': 'TO-ADDRESS-LINE-1',
        'Mandatory': 'Y',
        'Data type': 'A35',
        'Comment': """
            Must be present - PAF validation by Notify Must match
            PAF (in combination with TO-POST-CODE) to maximise
            postage discount
        """,
        'Example': '123 Electric Avenue',
    },
    {
        'Field number': '21',
        'Field name': 'TO-ADDRESS-LINE-2',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': """
            Address lines 2 through 5 are optional Composition
            process will remove blank address lines
        """,
        'Example': 'Great Yarmouth',
    },
    {
        'Field number': '22',
        'Field name': 'TO-ADDRESS-LINE-3',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': 'Norfolk',
    },
    {
        'Field number': '23',
        'Field name': 'TO-ADDRESS-LINE-4',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '24',
        'Field name': 'TO-ADDRESS-LINE-5',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '25',
        'Field name': 'TO-POST-CODE',
        'Mandatory': 'Y',
        'Data type': 'A8',
        'Comment': """,
            Unformatted (ie. SA6 7JL not SA067JL) Must be present -
            PAF validation by Notify Must match PAF (in combination
            with TO-ADDRESS-LINE-1) to maximise postage discount
        """,
        'Example': 'NR1 5PQ',
    },
    {
        'Field number': '26',
        'Field name': 'RETURN-NAME',
        'Mandatory': '',
        'Data type': 'A40',
        'Comment': """
            This section added to handle return of undelivered mail
            to a specific organisational address may be required in
            a later release of the service.

            Not used by Notify at the moment.

            Given example:
                DWP Pension Service
        """,
        'Example': '',
    },
    {
        'Field number': '27',
        'Field name': 'RETURN-ADDRESS-LINE-1',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': """
            Not used by Notify at the moment.

            Given example:
                Mail Handling Site A
        """,
        'Example': '',
    },
    {
        'Field number': '28',
        'Field name': 'RETURN-ADDRESS-LINE-2',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': """
            Not used by Notify at the moment.

            Given example:
                Wolverhampton
        """,
        'Example': '',
    },
    {
        'Field number': '29',
        'Field name': 'RETURN-ADDRESS-LINE-3',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '30',
        'Field name': 'RETURN-ADDRESS-LINE-4',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '31',
        'Field name': 'RETURN-ADDRESS-LINE-5',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '32',
        'Field name': 'RETURN-POST-CODE',
        'Mandatory': '',
        'Data type': 'A8',
        'Comment': """
            Not used by Notify at the moment.

            Given example:
                WV9 1LU
        """,
        'Example': '',
    },
    {
        'Field number': '33',
        'Field name': 'SUBJECT-LINE',
        'Mandatory': '',
        'Data type': 'A120',
        'Comment': """
            Not used by Notify any more, passed in the body

            Your application is due soon
        """,
        'Example': '',
    },
    {
        'Field number': '34',
        'Field name': 'NOTIFICATION-BODY',
        'Mandatory': '',
        'Data type': 'A',
        'Comment': """
            Difficult to define a maximum length as dependent on
            other formatting factors absolute maximum for OSG is 6
            pages but ideally no more than 4 pages total. OSG to
            confirm approach to mark up and line breaks...
        """,
        'Example': (
            '29 April 2016<cr><cr>'
            '<h1>Your application is something & something<normal><cr><cr>'
            'Dear Henry Hadlow,<cr><cr>'
            'Thank you for applying to register a lasting power of '
            'attorney (LPA) for property and financial affairs. We '
            'have checked your application and...<cr><cr>'
        ),
    }
]


@pytest.mark.parametrize('template_class', [
    SMSMessageTemplate,
    SMSPreviewTemplate,
])
def test_message_too_long(template_class):
    body = ('b' * 400) + '((foo))'
    template = template_class({'content': body}, prefix='a' * 100, values={'foo': 'c' * 200})
    assert template.is_message_too_long() is True


@pytest.mark.parametrize('template_class, kwargs', [
    (EmailPreviewTemplate, {}),
    (HTMLEmailTemplate, {}),
    (PlainTextEmailTemplate, {}),
])
def test_non_sms_ignores_message_too_long(template_class, kwargs):
    body = 'a' * 1000
    template = template_class({'content': body, 'subject': 'foo'}, **kwargs)
    assert template.is_message_too_long() is False


@pytest.mark.parametrize('subject', [
    ' no break ',
    ' no\tbreak ',
    '\tno break\t',
    'no \r\nbreak',
    'no \nbreak',
    'no \rbreak',
    '\rno break\n',
])
@pytest.mark.parametrize('template_class, extra_args', [
    (PlainTextEmailTemplate, {}),
    (HTMLEmailTemplate, {}),
    (EmailPreviewTemplate, {}),
])
def test_whitespace_in_subjects(template_class, subject, extra_args):

    template_instance = template_class(
        {'content': 'foo', 'subject': subject},
        **extra_args
    )
    assert template_instance.subject == 'no break'


@pytest.mark.parametrize('template_class', [
    WithSubjectTemplate,
    EmailPreviewTemplate,
    HTMLEmailTemplate,
    PlainTextEmailTemplate,
])
def test_whitespace_in_subject_placeholders(template_class):
    assert template_class(
        {'content': '', 'subject': '\u200C Your tax   ((status))'},
        values={'status': ' is\ndue '}
    ).subject == 'Your tax is due'


@pytest.mark.parametrize(
    'template_class, expected_output',
    [
        (
            PlainTextEmailTemplate,
            'paragraph one\n\n\xa0\n\nparagraph two',
        ),
        (
            HTMLEmailTemplate,
            (
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">paragraph one</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">\xa0</p>\n'
                '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">paragraph two</p>\n'
            ),
        ),
    ],
    ids=['plain', 'html']
)
def test_govuk_email_whitespace_hack(template_class, expected_output):

    template_instance = template_class({
        'content': 'paragraph one\n\n&nbsp;\n\nparagraph two',
        'subject': 'foo'
    })
    assert expected_output in str(template_instance)


def test_plain_text_email_whitespace():
    email = PlainTextEmailTemplate({'subject': 'foo', 'content': (
        '# Heading\n'
        '\n'
        '1. one\n'
        '2. two\n'
        '3. three\n'
        '\n'
        '***\n'
        '\n'
        '# Heading\n'
        '\n'
        'Paragraph\n'
        '\n'
        'Paragraph\n'
        '\n'
        '^ callout\n'
        '\n'
        '1. one not four\n'
        '1. two not five'
    )})
    assert str(email) == (
        'Heading\n'
        '-----------------------------------------------------------------\n'
        '1. one\n'
        '2. two\n'
        '3. three\n'
        '\n'
        '=================================================================\n'
        '\n'
        '\n\nHeading\n'
        '-----------------------------------------------------------------\n'
        'Paragraph\n'
        '\n'
        'Paragraph\n'
        '\n'
        '\n\ncallout\n\n\n\n'
        '1. one not four\n'
        '2. two not five\n'
        '\n'
    )


@pytest.mark.parametrize(
    'renderer, expected_content',
    (
        (PlainTextEmailTemplate, (
            'Heading link: https://example.com\n'
            '-----------------------------------------------------------------\n'
        )),
        (HTMLEmailTemplate, (
            '<h1 style="Margin: 0 0 20px 0; padding: 0; font-size: 32px; '
            'line-height: 35px; font-weight: bold; color: #323A45;">'
            'Heading <a style="word-wrap: break-word; color: #004795;" '
            'target="_blank" href="https://example.com">link</a>'
            '</h1>\n'
        )),
    ),
    ids=['PlainTextEmailTemplate', 'HTMLEmailTemplate']
)
def test_heading_only_template_renders(renderer, expected_content):
    assert expected_content in str(renderer(
        {
            'subject': 'foo',
            'content': '# Heading [link](https://example.com)',
        }
    ))


@pytest.mark.parametrize(
    'template_type, expected_content',
    (
        (PlainTextEmailTemplate, 'Hi\n\n\n\nThis is a block quote.\n\n\n\nhello\n\n'),
        (HTMLEmailTemplate, (
            f'<p style="{PARAGRAPH_STYLE}">Hi</p>\n'
            f'<blockquote style="{BLOCK_QUOTE_STYLE}">\n'
            f'<p style="{PARAGRAPH_STYLE}">This is a block quote.</p>\n'
            '</blockquote>\n'
            f'<p style="{PARAGRAPH_STYLE}">hello</p>\n'
        )),
    ),
    ids=['plain', 'html']
)
def test_block_quotes(template_type, expected_content):
    """
    Template markup uses ^ to denote a block quote, but Github markdown, which Mistune reflects, specifies a block
    quote with the > character.  Rather than write a custom parser, templates should preprocess their text to replace
    the former with the latter.
    """

    assert expected_content in str(
        template_type({'content': '\nHi\n\n^ This is a block quote.\n\nhello', 'subject': ''})
    )


@pytest.mark.parametrize(
    'template_type, expected',
    [
        (PlainTextEmailTemplate, '1. one\n2. two\n3. three\n'),
        (
            HTMLEmailTemplate,
            f'<ol role="presentation" style="{ORDERED_LIST_STYLE}">\n'
            f'<li style="{LIST_ITEM_STYLE}">one</li>\n'
            f'<li style="{LIST_ITEM_STYLE}">two</li>\n'
            f'<li style="{LIST_ITEM_STYLE}">three</li>\n'
            '</ol>\n'
        ),
    ]
)
def test_ordered_list_without_spaces(template_type, expected):
    """
    Proper markdown for ordered lists has a space after the number and period.
    """

    content = '1.one\n2.two\n3.three\n'

    if isinstance(template_type, PlainTextEmailTemplate):
        assert str(template_type({'content': content, 'subject': ''})) == expected
    else:
        assert expected in str(template_type({'content': content, 'subject': ''}))


@pytest.mark.parametrize('with_spaces', [True, False])
@pytest.mark.parametrize(
    'template_type, expected',
    [
        (PlainTextEmailTemplate, '• one\n• two\n• three\n\n'),
        (
            HTMLEmailTemplate,
            f'<ul role="presentation" style="{UNORDERED_LIST_STYLE}">\n'
            f'<li style="{LIST_ITEM_STYLE}">one</li>\n'
            f'<li style="{LIST_ITEM_STYLE}">two</li>\n'
            f'<li style="{LIST_ITEM_STYLE}">three</li>\n'
            '</ul>\n'
        ),
    ]
)
@pytest.mark.parametrize('bullet', ['*', '-', '+', '•'])
def test_unordered_list(bullet, template_type, expected, with_spaces):
    """
    Proper markdown for unordered lists has a space after the bullet.
    """

    space = ' ' if with_spaces else ''
    content = f'{bullet}{space}one\n{bullet}{space}two\n{bullet}{space}three\n'

    if isinstance(template_type, PlainTextEmailTemplate):
        assert str(template_type({'content': content, 'subject': ''})) == expected
    else:
        assert expected in str(template_type({'content': content, 'subject': ''}))

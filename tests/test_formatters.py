import pytest
from markupsafe import Markup

from notifications_utils.formatters import (
    unlink_govuk_escaped,
    sms_encode,
    formatted_list,
    strip_dvla_markup,
    strip_pipes,
    escape_html,
    remove_whitespace_before_punctuation,
    make_quotes_smart,
    replace_hyphens_with_en_dashes,
    tweak_dvla_list_markup,
    nl2li,
    strip_whitespace,
    strip_and_remove_obscure_whitespace,
    remove_smart_quotes_from_email_addresses,
    strip_unsupported_characters,
    normalise_whitespace,
)
from notifications_utils.template import (
    HTMLEmailTemplate,
    PlainTextEmailTemplate,
    SMSMessageTemplate,
    SMSPreviewTemplate
)

PARAGRAPH_TEXT = '<p style="Margin: 0 0 20px 0; font-size: 16px; line-height: 25px; color: #323A45;">{}</p>'


def test_html_template_has_urls_replaced_with_links():
    assert (
        '<a style="word-wrap: break-word; color: #004795;" href="https://service.example.com/accept_invite/a1b2c3d4">'
        'https://service.example.com/accept_invite/a1b2c3d4'
        '</a>'
    ) in str(HTMLEmailTemplate({'content': (
        'You’ve been invited to a service. Click this link:\n'
        'https://service.example.com/accept_invite/a1b2c3d4\n'
        '\n'
        'Thanks\n'
    ), 'subject': ''}))


@pytest.mark.parametrize(
    "template_content,expected", [
        ("gov.uk", u"gov.\u200Buk"),
        ("GOV.UK", u"GOV.\u200BUK"),
        ("Gov.uk", u"Gov.\u200Buk"),
        ("https://gov.uk", "https://gov.uk"),
        ("https://www.gov.uk", "https://www.gov.uk"),
        ("www.gov.uk", "www.gov.uk"),
        ("gov.uk/register-to-vote", "gov.uk/register-to-vote"),
        ("gov.uk?q=", "gov.uk?q=")
    ]
)
def test_escaping_govuk_in_email_templates(template_content, expected):
    assert unlink_govuk_escaped(template_content) == expected
    assert expected in str(PlainTextEmailTemplate({'content': template_content, 'subject': ''}))
    assert expected in str(HTMLEmailTemplate({'content': template_content, 'subject': ''}))


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

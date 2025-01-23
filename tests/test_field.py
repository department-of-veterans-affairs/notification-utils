import pytest
from notifications_utils.field import Field, NullValueForNonConditionalPlaceholderException


@pytest.mark.parametrize("content", [
    "",
    "the quick brown fox",
    """
        the
        quick brown

        fox
    """,
    "the ((quick brown fox",
    "the (()) brown fox",
])
def test_returns_a_string_without_placeholders(content):
    assert str(Field(content)) == content


@pytest.mark.parametrize(
    "template_content,data,expected", [
        (
            "((colour))",
            {"colour": "red"},
            "red"
        ),
        (
            "the quick ((colour)) fox",
            {"colour": "brown"},
            "the quick brown fox"
        ),
        (
            "((article)) quick ((colour)) ((animal))",
            {"article": "the", "colour": "brown", "animal": "fox"},
            "the quick brown fox"
        ),
        (
            "the quick (((colour))) fox",
            {"colour": "brown"},
            "the quick (brown) fox"
        ),
        (
            "the quick ((colour)) fox",
            {"colour": "<script>alert('foo')</script>"},
            "the quick alert('foo') fox"
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': True},
            'before True after',
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': False},
            'before False after',
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': 0},
            'before 0 after',
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': 0.0},
            'before 0.0 after',
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': 123},
            'before 123 after',
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': 0.1 + 0.2},
            'before 0.30000000000000004 after',
        ),
        (
            'before ((placeholder)) after',
            {'placeholder': {"key": "value"}},
            'before {\'key\': \'value\'} after',
        ),
        (
            "((warning?))",             # This is not a valid palceholder
            {"warning?": "This is not a conditional"},
            "((warning?))"              # No substitution because it's not a valid placholder
        ),
        (
            "((warning?warning))",      # This is not a valid palceholder
            {"warning?warning": "This is not a conditional"},
            "((warning?warning))"     # No substitution because it's not a valid placholder
        ),
        (
            "((warning??This is a conditional warning))",
            {"warning": True},
            "This is a conditional warning"
        ),
        (
            "((warning??This is a conditional warning))",
            {"warning": False},
            ""
        ),
        (
            "((warning??This is a conditional warning: {}))",
            {"warning": "Tornado is coming"},
            "This is a conditional warning: Tornado is coming"
        ),
        (
            "((warning??This is a conditional warning: {}))",
            {"warning": True},
            "This is a conditional warning: True"
        ),
        (
            "((warning??This is a conditional warning: {}))",
            {"warning": ""},
            ""
        ),
        (
            "((warning??This is a conditional warning: {}))",
            {"warning": False},
            ""
        ),
        (
            "((url_param??Url with param: [static url name](http://test.me/{}) ))",
            {"url_param": "foo"},
            "Url with param: [static url name](http://test.me/foo) "
        ),
        (
            "((dynamic_url??Url with param: [{}]({}) ))",
            {"dynamic_url": "https://foo.bar"},
            "Url with param: [https://foo.bar](https://foo.bar) "
        ),
    ]
)
def test_replacement_of_placeholders(template_content, data, expected):
    assert str(Field(template_content, data)) == expected


def test_replacement_with_list_in_blockquote():
    """
    List substitution inside a block quote should not add new content outside of the block quote.
    """

    content = "^ This is a block quote with a list: ((the_list))"
    values = {"the_list": ["list item 1", "list item 2"]}
    expected = "^ This is a block quote with a list: \n^ * list item 1\n^ * list item 2"
    assert str(Field(content, values, markdown_lists=True)) == expected


@pytest.mark.parametrize(
    "template_content,data,expected", [
        (
            "((code)) is your security code",
            {"code": "12345"},
            "12345 is your security code"
        ),
        (
            "((code)) is your security code",
            {},
            "<span class='placeholder-redacted'>hidden</span> is your security code"
        ),
        (
            "Hey ((name)), click http://example.com/reset-password/?token=((token))",
            {'name': 'Example'},
            (
                "Hey Example, click "
                "http://example.com/reset-password/?token="
                "<span class='placeholder-redacted'>hidden</span>"
            )
        ),
    ]
)
def test_optional_redacting_of_missing_values(template_content, data, expected):
    assert str(Field(template_content, data, redact_missing_personalisation=True)) == expected


@pytest.mark.parametrize(
    "content,expected", [
        (
            "((colour))",
            "<span class='placeholder'>((colour))</span>"
        ),
        (
            "the quick ((colour)) fox",
            "the quick <span class='placeholder'>((colour))</span> fox"
        ),
        (
            "((article)) quick ((colour)) ((animal))",
            "<span class='placeholder'>((article))</span> quick <span class='placeholder'>((colour))</span> <span class='placeholder'>((animal))</span>"  # noqa
        ),
        (
            """
                ((article)) quick
                ((colour))
                ((animal))
            """,
            """
                <span class='placeholder'>((article))</span> quick
                <span class='placeholder'>((colour))</span>
                <span class='placeholder'>((animal))</span>
            """
        ),
        (
            "the quick (((colour))) fox",
            "the quick (<span class='placeholder'>((colour))</span>) fox"
        ),
        (
            "((warning?))",             # This is not a valid placeholder name
            "((warning?))"
        ),
        (
            "((warning? This is not a conditional))",       # This is not a valid placeholder name
            "((warning? This is not a conditional))"
        ),
        (
            "((warning?? This is a warning))",
            "<span class='placeholder-conditional'>((warning??</span> This is a warning))"
        ),
        (
            "((condition?? Let's use conditional value: {} here))",
            "<span class='placeholder-conditional'>((condition??</span> Let's use conditional value: {} here))"
        ),
        (
            "((url?? We can have conditional urls: [url](url) ))",
            "<span class='placeholder-conditional'>((url??</span> We can have conditional urls: [url](url) ))"
        ),
    ]
)
def test_formatting_of_placeholders(content, expected):
    assert str(Field(content)) == expected


def test_handling_of_missing_values():
    content = "((show_thing??thing)) ((colour))"
    values = {'colour': 'red'}
    expected = "<span class='placeholder-conditional'>((show_thing??</span>thing)) red"

    assert str(Field(content, values)) == expected


@pytest.mark.parametrize("values, expected, expected_as_markdown", [
    (
        {'placeholder': ['one']},
        'list: one',
        'list: \n\n* one',
    ),
    (
        {'placeholder': ['one', 'two']},
        'list: one and two',
        'list: \n\n* one\n* two',
    ),
    (
        {'placeholder': ['one', 'two', 'three']},
        'list: one, two and three',
        'list: \n\n* one\n* two\n* three',
    ),
    (
        {'placeholder': ['one', None, None]},
        'list: one',
        'list: \n\n* one',
    ),
    (
        {'placeholder': ['<script>', 'alert("foo")', '</script>']},
        'list: , alert("foo") and ',
        'list: \n\n* \n* alert("foo")\n* ',
    ),
    (
        {'placeholder': [1, {'two': 2}, 'three', None]},
        'list: 1, {\'two\': 2} and three',
        'list: \n\n* 1\n* {\'two\': 2}\n* three',
    ),
    (
        {'placeholder': [[1, 2], [3, 4]]},
        'list: [1, 2] and [3, 4]',
        'list: \n\n* [1, 2]\n* [3, 4]',
    ),
])
def test_field_renders_lists_as_strings(values, expected, expected_as_markdown):
    assert str(Field("list: ((placeholder))", values, markdown_lists=True)) == expected_as_markdown
    assert str(Field("list: ((placeholder))", values)) == expected


def test_that_field_renders_fine_if_in_preview_mode_and_null_values_for_placeholder():
    template_content = "this is ((some_non_conditional_field)) to test"
    data = {"some_non_conditional_field": None}
    expected_value = "this is <span class='placeholder'><mark>((some_non_conditional_field))</mark></span> to test"

    assert str(Field(template_content, data, preview_mode=True)) == expected_value


def test_that_field_renders_fine_if_not_in_preview_mode_and_null_values_for_conditional_placeholders():
    template_content = "this is ((some_non_conditional_field??)) to test"
    data = {"some_non_conditional_field": None}
    expected_value = "this is <span class='placeholder-conditional'>((some_non_conditional_field??</span>)) to test"

    assert str(Field(template_content, data, preview_mode=False)) == expected_value


def test_that_error_is_thrown_if_not_in_preview_mode_and_null_values_for_placeholder():
    template_content = "this is ((some_non_conditional_field)) to test"
    data = {"some_non_conditional_field": None}

    with pytest.raises(NullValueForNonConditionalPlaceholderException):
        str(Field(template_content, data, preview_mode=False))

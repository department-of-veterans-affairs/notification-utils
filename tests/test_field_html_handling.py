import pytest
from notifications_utils.field import Field


@pytest.mark.parametrize('content, values, expected_stripped, expected_escaped, expected_passthrough', [
    (
        'string <em>with</em> html',
        {},
        'string with html',
        'string &lt;em&gt;with&lt;/em&gt; html',
        'string <em>with</em> html',
    ),
    (
        'string ((<em>with</em>)) html',        # This is not a valid placeholder name
        {},
        # Stripping will make it into a valid placeholder
        'string <span class=\'placeholder\'>((with))</span> html',
        'string ((&lt;em&gt;with&lt;/em&gt;)) html',
        'string ((<em>with</em>)) html',
    ),
    (
        'string ((placeholder)) html',
        {'placeholder': '<em>without</em>'},
        'string without html',
        'string &lt;em&gt;without&lt;/em&gt; html',
        'string <em>without</em> html',
    ),
    (
        'string ((<em>conditional</em>??<em>placeholder</em>)) html',       # This is not a valid placeholder name
        {},
        # Stripping will make it into a valid placeholder
        'string <span class=\'placeholder-conditional\'>((conditional??</span>placeholder)) html',
        (
            'string '
            '((&lt;em&gt;conditional&lt;/em&gt;??'
            '&lt;em&gt;placeholder&lt;/em&gt;)) '
            'html'
        ),
        (
            'string '
            '((<em>conditional</em>??'
            '<em>placeholder</em>)) '
            'html'
        ),
    ),
    (
        'string ((conditional??<em>placeholder</em>)) html',
        {'conditional': True},
        'string placeholder html',
        'string &lt;em&gt;placeholder&lt;/em&gt; html',
        'string <em>placeholder</em> html',
    ),
    (
        'string & entity',
        {},
        'string &amp; entity',
        'string &amp; entity',
        'string & entity',
    ),
],
    ids=[
        'string with html',
        'string with html inside placeholder',
        'string with placeholder',
        'string with html inside conditional placeholder',
        'string with conditional placeholder with html after condition',
        'string with special character &',
]
)
def test_field_handles_html(content, values, expected_stripped, expected_escaped, expected_passthrough):
    assert str(Field(content, values)) == expected_stripped
    assert str(Field(content, values, html='strip')) == expected_stripped
    assert str(Field(content, values, html='escape')) == expected_escaped
    assert str(Field(content, values, html='passthrough')) == expected_passthrough

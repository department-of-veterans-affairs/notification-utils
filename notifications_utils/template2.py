import re
from os import path
from typing import Match

from jinja2 import Environment, FileSystemLoader

from notifications_utils.formatters2 import (
    insert_action_links,
    notify_html_markdown,
    notify_markdown,
)

PLACEHOLDER_REGEX = re.compile(r'\(\((?P<key>\w+)\)\)')

jinja2_env = Environment(loader=FileSystemLoader(path.join(path.dirname(path.abspath(__file__)), 'jinja_templates')))


def render_notify_markdown(markdown: str, personalization: dict | None = None, as_html: bool = True) -> str:
    """
    Return markdown as HTML or plain text, and perform substitutions with personalization data, if any.
    """

    if not (personalization is None or isinstance(personalization, dict)):
        raise TypeError('Personalization should be a dictionary or None.')

    # Passing markdown with placeholders of the format ((key)) can break Mistune.
    # Convert this syntax to something that won't break Mistune.
    markdown = PLACEHOLDER_REGEX.sub(r'PLACEHOLDER_\g<key>_PLACEHOLDER', markdown)

    # Perform all pre-processing steps to handle non-standard markdown.
    # TODO #243 - Use a Mistune plug-in for action links
    markdown = insert_action_links(markdown, as_html)

    rendered = notify_html_markdown(markdown) if as_html else notify_markdown(markdown)

    if personalization:
        rendered = make_substitutions(rendered, personalization, as_html)

    return rendered


def make_substitutions(template: str, personalization: dict, as_html: bool) -> str:  # noqa C901
    """
    Given a template this has already been converted to HTML or plain text, as indicated by the "as_html"
    parameter, substitute personalized values.

    Ensure that spaces in URLs, if any, are properly escaped so the content displays correctly in an e-mail
    client.  For HTML, escaping is straight forward after substitution because URLs appear in an href attribute.

    For plain text, escaping must happen before substitution.  Otherwise, there is no way to recongnize that
    text following a link is not part of the link.
    """

    placeholders = re.findall(r'(http)?(?:\S*?PLACEHOLDER_)(\S+?)(?:_PLACEHOLDER)', template)
    unique_placeholders = frozenset((key) for _, key in placeholders)

    if len(personalization) < len(unique_placeholders):
        missing_personalization = ','.join(key for key in unique_placeholders if key not in personalization)
        raise ValueError(f'Missing required personalization: {missing_personalization}')

    if not as_html:
        # Escape whitespace in plain text URLs, if any.
        for key in personalization:
            if isinstance(personalization[key], list):
                # Users should not insert list values into URLs, so don't attempt to escape them.
                continue

            if 'http' in personalization[key].lower() or any((bool(http)) for http, k in placeholders if k == key):
                # The value either is a complete URL or is part of a URL (ex. query parameters).
                personalization[key] = re.sub(r'\s', encode_whitespace, personalization[key])

    for key, value in personalization.items():
        if isinstance(value, list):
            if as_html:
                substitution = '\n<ul>\n' + '\n'.join((f'<li>{li}</li>') for li in value) + '\n</ul>\n'
            else:
                substitution = '\n' + '\n'.join((f'• {li}') for li in value) + '\n'
        else:
            substitution = value

        template = template.replace(f'PLACEHOLDER_{key}_PLACEHOLDER', substitution)

    if as_html:
        # Escape whitespace in HTML URLs, if any.
        template = re.sub(r'(?<=href=")(?P<url>.+?)(?=")', encode_whitespace, template)

    return template


def encode_whitespace(m: Match[str]) -> str:
    """
    Replace each whitespace character in the matched text with its percent-encoded form.
    """

    return re.sub(r'\s', lambda m: f'%{ord(m.group(0)):02X}', m.group(0))


def render_html_email(
    content: str,
    preheader: str | None = None,
    ga4_open_email_event_url: str | None = None,
) -> str:
    """
    Return the text of an HTML e-mail by substituting the parameters into a Jinja2 template.
    The template should include all CSS styling for the message.
    """

    template = jinja2_env.get_template('email_template2.jinja2')

    return template.render(
        {
            'body': content,
            'preheader': preheader,
            'ga4_open_email_event_url': ga4_open_email_event_url,
        }
    )

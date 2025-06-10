import re

from notifications_utils.formatters2 import (
    insert_action_links,
    notify_html_markdown,
    notify_markdown,
)

# TODO - Does this need to accept whitespace?
PLACEHOLDER_REGEX = re.compile(r'\(\((?P<key>\w+)\)\)')


def render_notify_markdown(markdown: str, personalization: dict | None = None, as_html: bool = True) -> str:
    """
    Return markdown as HTML or plain text, and perform substitutions with personalization data, if any.
    """

    if not (personalization is None or isinstance(personalization, dict)):
        raise TypeError('Personalization should be a dictionary or None.')

    # Passing markdown with placeholders of the format ((key)) can break Mistune.
    # Convert this syntax to something that won't break Mistune.
    markdown = PLACEHOLDER_REGEX.sub('\g<key>_PLACEHOLDER', markdown)  # noqa W605

    # Perform all pre-processing steps to handle non-standard markdown.
    # TODO #243 - Use a Mistune plug-in for action links
    markdown = insert_action_links(markdown, as_html)

    rendered = notify_html_markdown(markdown) if as_html else notify_markdown(markdown)

    if personalization:
        rendered = make_substitutions(rendered, personalization, as_html)

    return rendered


def make_substitutions(template: str, personalization: dict, as_html: bool) -> str:
    for key, value in personalization.items():
        if isinstance(value, list):
            if as_html:
                substitution = '\n<ul>\n' + '\n'.join((f'<li>{li}</li>') for li in value) + '\n</ul>\n'
            else:
                substitution = '\n'.join((f'• {li}') for li in value) + '\n'
        else:
            substitution = value

        template = template.replace(f'{key}_PLACEHOLDER', substitution)

    return template


# TODO - The signature and return type might change for #215 or later, during integration with notifcation-api.
def render_email(
    html_content: str | None = None,
    plain_text_content: str | None = None,
    subject_personalization: dict | None = None
) -> tuple[str | None, str | None]:
    """
    In addition to the content body, e-mail notifications might have personalization values in the
    subject line, and the content body might be plugged into a Jinja2 template.

    The two "content" parameters generally are the output of render_notify_markdown (above).

    returns: A 2-tuple in which the first value is the full HTML e-mail; the second, the plain text e-mail.
    """

    if html_content is None and plain_text_content is None:
        raise ValueError('You must supply one of these parameters.')

    # TODO #215 - Perform substitutions in the subject.  Raise ValueError for missing fields.
    # TODO #215 - Jinja2 template substitution

    raise NotImplementedError

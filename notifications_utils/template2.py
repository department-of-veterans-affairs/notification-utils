def render_notify_markdown(markdown: str, personalization: dict = {}, as_html: bool = True) -> str:
    """
    Substitute personalization values into markdown, and return the markdown as HTML or plain text.
    """

    # TODO - Perform substitutions in the markdown.  Raise ValueError for missing fields.

    if as_html:
        # TODO - pass the markdown to the HTML renderer
        pass
    else:
        # TODO - pass the markdown to the plain text renderer
        pass

    raise NotImplementedError


# TODO - The signature and return type might change after #213, during integration with notifcation-api.
def render_email(
    html_content: str | None = None,
    plain_text_content: str | None = None,
    subject_personalization: dict = {}
) -> tuple[str | None, str | None]:
    """
    In addition to the content body, e-mail notifications might have personalization values in the
    subject line, and the content body might be plugged into a Jinja2 template.

    The two "content" parameters generally are the output of render_notify_markdown (above).

    returns: A 2-tuple in which the first value is the full HTML e-mail; the second, the plain text e-mail.
    """

    if html_content is None and plain_text_content is None:
        raise ValueError('You must supply one of these parameters.')

    # TODO - Perform substitutions in the subject.  Raise ValueError for missing fields.
    # TODO - Jinja2 template substitution

    raise NotImplementedError

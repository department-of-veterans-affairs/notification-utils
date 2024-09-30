import math
import sys
from os import path

import mistune
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from notifications_utils import SMS_CHAR_COUNT_LIMIT
from notifications_utils.columns import Columns
from notifications_utils.field import Field
from notifications_utils.sanitise_text import SanitiseSMS
from notifications_utils.template_change import TemplateChange

template_env = Environment(loader=FileSystemLoader(
    path.join(
        path.dirname(path.abspath(__file__)),
        'jinja_templates',
    )
))


class Template():

    encoding = "utf-8"

    def __init__(
        self,
        template,
        values=None,
        redact_missing_personalisation=False,
        jinja_path=None
    ):
        if not isinstance(template, dict):
            raise TypeError('Template must be a dict')
        if values is not None and not isinstance(values, dict):
            raise TypeError('Values must be a dict')
        self.id = template.get("id", None)
        self.name = template.get("name", None)
        self.content = template["content"]
        self.values = values
        self.template_type = template.get('template_type', None)
        self._template = template
        self.redact_missing_personalisation = redact_missing_personalisation
        if (jinja_path is not None):
            self.template_env = Environment(loader=FileSystemLoader(
                path.join(
                    path.dirname(jinja_path),
                    'jinja_templates',
                )
            ))
        else:
            self.template_env = Environment(loader=FileSystemLoader(
                path.join(
                    path.dirname(path.abspath(__file__)),
                    'jinja_templates',
                )
            ))

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.content}", {self.values})'

    def __str__(self):
        return Markup(Field(
            self.content,
            self.values,
            html='escape',
            redact_missing_personalisation=self.redact_missing_personalisation,
        ))

    @property
    def values(self):
        if hasattr(self, '_values'):
            return self._values
        return {}

    @values.setter
    def values(self, value):
        if not value:
            self._values = {}
        else:
            placeholders = Columns.from_keys(self.placeholders)
            self._values = Columns(value).as_dict_with_keys(
                self.placeholders | set(
                    key for key in value.keys()
                    if Columns.make_key(key) not in placeholders.keys()
                )
            )

    @property
    def placeholders(self):  # TODO: rename to placeholder_names
        return Field(self.content).placeholder_names

    @property
    def missing_data(self):
        return list(
            placeholder_name for placeholder_name in Field(self.content).placeholder_names
            if self.values.get(placeholder_name) is None
        )

    @property
    def additional_data(self):
        return self.values.keys() - self.placeholders

    def get_raw(self, key, default=None):
        return self._template.get(key, default)

    def compare_to(self, new):
        return TemplateChange(self, new)

    def is_message_too_long(self):
        return False


def add_prefix(body, prefix=None):
    if prefix:
        return f"{prefix.strip()}: {body}"
    return body


class SMSMessageTemplate(Template):

    def __init__(
        self,
        template,
        values=None,
        prefix=None,
        show_prefix=True,
        sender=None,
        jinja_path=None
    ):
        self.prefix = prefix
        self.show_prefix = show_prefix
        self.sender = sender
        super().__init__(template, values, jinja_path=jinja_path)

    def __str__(self):
        return Field(self.content, self.values, html='passthrough')

    @property
    def prefix(self):
        return self._prefix if self.show_prefix else None

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def content_count(self):
        return len((
            # we always want to call SMSMessageTemplate.__str__ regardless of subclass, to avoid any html formatting
            SMSMessageTemplate.__str__(self)
            if self._values
            else SanitiseSMS.encode(add_prefix(self.content.strip(), self.prefix))
        ).encode(self.encoding))

    @property
    def fragment_count(self):
        content_with_placeholders = str(self)
        return get_sms_fragment_count(self.content_count, is_unicode(content_with_placeholders))

    def is_message_too_long(self):
        return self.content_count > SMS_CHAR_COUNT_LIMIT


class SMSPreviewTemplate(SMSMessageTemplate):

    def __init__(
        self,
        template,
        values=None,
        prefix=None,
        show_prefix=True,
        sender=None,
        show_recipient=False,
        show_sender=False,
        downgrade_non_sms_characters=True,
        redact_missing_personalisation=False,
        jinja_path=None
    ):
        self.show_recipient = show_recipient
        self.show_sender = show_sender
        self.downgrade_non_sms_characters = downgrade_non_sms_characters
        super().__init__(template, values, prefix, show_prefix, sender, jinja_path=jinja_path)
        self.redact_missing_personalisation = redact_missing_personalisation
        self.jinja_template = self.template_env.get_template('sms_preview_template.jinja2')

    def __str__(self):

        return Markup(self.jinja_template.render({
            'sender': self.sender,
            'show_sender': self.show_sender,
            'recipient': Field('((phone number))', self.values, with_brackets=False, html='escape'),
            'show_recipient': self.show_recipient,
            'body': Field(
                self.content,
                self.values,
                html='escape',
                redact_missing_personalisation=self.redact_missing_personalisation,
            )
        }))


class WithSubjectTemplate(Template):

    def __init__(
        self,
        template,
        values=None,
        redact_missing_personalisation=False,
        jinja_path=None,
    ):
        self._subject = template['subject']
        super().__init__(template,
                         values,
                         redact_missing_personalisation=redact_missing_personalisation,
                         jinja_path=jinja_path)

    def __str__(self):
        return str(Field(
            self.content,
            self.values,
            html='passthrough',
            redact_missing_personalisation=self.redact_missing_personalisation,
            markdown_lists=True,
        ))

    @property
    def subject(self):
        return Markup(Field(
            self._subject,
            self.values,
            html='escape',
            redact_missing_personalisation=self.redact_missing_personalisation,
        ))

    @property
    def placeholders(self):
        return Field(self._subject).placeholder_names | Field(self.content).placeholder_names


class PlainTextEmailTemplate(WithSubjectTemplate):

    def __str__(self):
        return Field(
            self.content, self.values, html='passthrough', markdown_lists=True
        )

    @property
    def subject(self):
        return Markup(Field(
            self._subject,
            self.values,
            html='passthrough',
            redact_missing_personalisation=self.redact_missing_personalisation
        ))


class HTMLEmailTemplate(WithSubjectTemplate):

    # Instantiate with regular jinja for test mocking (tests expect this to exist before init)
    jinja_template = template_env.get_template('email_template.jinja2')

    PREHEADER_LENGTH_IN_CHARACTERS = 256

    def __init__(
        self,
        template,
        values=None,
        default_banner=True,
        complete_html=True,
        brand_logo=None,
        brand_text=None,
        brand_colour=None,
        brand_banner=False,
        brand_name=None,
        jinja_path=None,
        ga_pixel_url=None,
        ga4_open_email_event_url=None,
        preview_mode=False
    ):
        super().__init__(template, values, jinja_path=jinja_path)
        self.default_banner = default_banner
        self.complete_html = complete_html
        self.brand_logo = brand_logo
        self.brand_text = brand_text
        self.brand_colour = brand_colour
        self.brand_banner = brand_banner
        self.brand_name = brand_name
        self.ga_pixel_url = ga_pixel_url
        self.ga4_open_email_event_url = ga4_open_email_event_url
        self.preview_mode = preview_mode
        # set this again to make sure the correct either utils / downstream local jinja is used
        # however, don't set if we are in a test environment (to preserve the above mock)
        if "pytest" not in sys.modules:
            self.jinja_template = self.template_env.get_template('email_template.jinja2')

    @property
    def preheader(self):
        return " ".join(Field(
            self.content,
            self.values,
            html='escape',
            markdown_lists=True
        )).split()[:self.PREHEADER_LENGTH_IN_CHARACTERS].strip()

    def __str__(self):

        return self.jinja_template.render({
            'body': get_html_email_body(
                self.content, self.values, preview_mode=self.preview_mode
            ),
            'preheader': self.preheader if not self.preview_mode else '',
            'default_banner': self.default_banner,
            'complete_html': self.complete_html,
            'brand_logo': self.brand_logo,
            'brand_text': self.brand_text,
            'brand_colour': self.brand_colour,
            'brand_banner': self.brand_banner,
            'brand_name': self.brand_name,
            'ga_pixel_url': self.ga_pixel_url,
            'ga4_open_email_event_url': self.ga4_open_email_event_url,
            'preview_mode': self.preview_mode,
            'path_to_js_script': path.join(
                path.dirname(path.abspath(__file__)), 'static/iframeResizer.contentWindow.min.js'
            )
        })


class EmailPreviewTemplate(WithSubjectTemplate):

    def __init__(
        self,
        template,
        values=None,
        from_name=None,
        from_address=None,
        reply_to=None,
        show_recipient=True,
        redact_missing_personalisation=False,
        jinja_path=None,
    ):
        super().__init__(template,
                         values,
                         redact_missing_personalisation=redact_missing_personalisation,
                         jinja_path=jinja_path)
        self.from_name = from_name
        self.from_address = from_address
        self.reply_to = reply_to
        self.show_recipient = show_recipient
        self.jinja_template = self.template_env.get_template('email_preview_template.jinja2')

    def __str__(self):
        return Markup(self.jinja_template.render({
            'body': get_html_email_body(
                self.content, self.values, redact_missing_personalisation=self.redact_missing_personalisation
            ),
            'subject': self.subject,
            'from_name': mistune.escape(self.from_name),
            'from_address': self.from_address,
            'reply_to': self.reply_to,
            'recipient': Field("((email address))", self.values, with_brackets=False),
            'show_recipient': self.show_recipient
        }))

    @property
    def subject(self):
        return Field(
            self._subject,
            self.values,
            html='escape',
            redact_missing_personalisation=self.redact_missing_personalisation
        )


class NeededByTemplateError(Exception):
    def __init__(self, keys):
        super(NeededByTemplateError, self).__init__(", ".join(keys))


class NoPlaceholderForDataError(Exception):
    def __init__(self, keys):
        super(NoPlaceholderForDataError, self).__init__(", ".join(keys))


def get_sms_fragment_count(character_count, is_unicode):
    if is_unicode:
        return 1 if character_count <= 70 else math.ceil(float(character_count) / 67)
    else:
        return 1 if character_count <= 160 else math.ceil(float(character_count) / 153)


def is_unicode(content):
    return set(content) & set(SanitiseSMS.WELSH_NON_GSM_CHARACTERS)


def get_html_email_body(
    template_content: dict, template_values: dict, redact_missing_personalisation=False, preview_mode=False
) -> str:
    """
    Substitute the personalized values into the template markdown, and convert the result to HTML.
    """

    personalized_content = Field(
        template_content,
        template_values,
        html='escape',
        markdown_lists=True,
        redact_missing_personalisation=redact_missing_personalisation,
        preview_mode=preview_mode
    )

    return mistune.html(Markup(personalized_content))

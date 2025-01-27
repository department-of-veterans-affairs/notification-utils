import re

from markupsafe import Markup

from notifications_utils.columns import Columns
from notifications_utils.formatters import (
    unescaped_formatted_list,
    strip_html,
    escape_html,
    strip_dvla_markup,
)


class Placeholder:

    def __init__(self, body):
        # body should not include the (( and )).
        self.body = body.lstrip('((').rstrip('))')

    @classmethod
    def from_match(cls, match):
        return cls(match.group(0))

    def is_conditional(self):
        return '??' in self.body

    @staticmethod
    def should_render_conditional(palceholder_value: str) -> bool:
        if str(palceholder_value) in ['', 'False']:
            return False
        return True

    @property
    def name(self):
        # for non conditionals, name equals body
        return self.body.split('??')[0]

    @property
    def conditional_text(self):
        if self.is_conditional():
            # ((a?? b??c)) returns " b??c"
            return '??'.join(self.body.split('??')[1:])
        else:
            raise ValueError('{} not conditional'.format(self))

    def get_conditional_body(self, placeholder_value):
        # note: unsanitised/converted
        if self.is_conditional():
            return self.conditional_text if self.should_render_conditional(placeholder_value) else ''
        else:
            raise ValueError('{} not conditional'.format(self))

    def __repr__(self):
        return 'Placeholder({})'.format(self.body)


class Field:
    placeholder_pattern = re.compile(
        # this is simply the below regex on one line for easier analysis
        # r'\({2}([\w \-]+(?:\?{2}.*?(?!\({2}[\w \-]+\){2}.*?))?)\){2}'
        r'\({2}'        # opening ((
        r'('            # start capture group
        r'[\w \-]+'     # placeholder name that allows only alpha numberic characters, space and dash
        r'(?:'          # start non-capture group
        r'\?{2}'        # match ?? for conditional placeholder
        r'.*?(?!\({2}[\w \-]+\){2}.*?)'     # negative lookeahead to prevent matching when there is a nested placeholder
        r')?'           # end optional non-capture group
        r')'            # end capture group
        r'\){2}'        # closing ))
    )
    conditional_placeholder_pattern = re.compile(
        r'(\{\})'  # look for just '{}' inside conditional block
    )
    placeholder_tag = "<span class='placeholder'>(({}))</span>"
    placeholder_tag_with_highlight = "<span class='placeholder'><mark>(({}))</mark></span>"
    conditional_placeholder_tag = "<span class='placeholder-conditional'>(({}??</span>{}))"
    placeholder_tag_no_brackets = "<span class='placeholder-no-brackets'>{}</span>"
    placeholder_tag_redacted = "<span class='placeholder-redacted'>hidden</span>"

    def __init__(
        self,
        content,
        values=None,
        with_brackets=True,
        html='strip',
        markdown_lists=False,
        redact_missing_personalisation=False,
        preview_mode=False,
    ):
        self.content = content
        self.values = values
        self.markdown_lists = markdown_lists
        self.preview_mode = preview_mode
        if not with_brackets:
            self.placeholder_tag = self.placeholder_tag_no_brackets
        if preview_mode:
            self.placeholder_tag = self.placeholder_tag_with_highlight
        self.sanitizer = {
            'strip': strip_html,
            'escape': escape_html,
            'passthrough': str,
            'strip_dvla_markup': strip_dvla_markup,
        }[html]
        self.redact_missing_personalisation = redact_missing_personalisation

    def __str__(self) -> str:
        if self.values:
            return self.replaced
        return str(self.formatted)

    def __repr__(self):
        return "{}(\"{}\", {})".format(self.__class__.__name__, self.content, self.values)  # TODO: more real

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        self._values = Columns(value) if value else {}

    def format_match(self, match):
        placeholder = Placeholder.from_match(match)

        if self.redact_missing_personalisation:
            return self.placeholder_tag_redacted

        if placeholder.is_conditional():
            return self.conditional_placeholder_tag.format(
                self.sanitizer(placeholder.name),
                self.sanitizer(placeholder.conditional_text)
            )

        return self.placeholder_tag.format(
            self.sanitizer(placeholder.name)
        )

    def replace_match(self, match):
        placeholder = Placeholder.from_match(match)
        replacement = self.values.get(placeholder.name)

        if placeholder.is_conditional() and replacement is not None:
            return re.sub(
                self.conditional_placeholder_pattern,
                self.sanitizer(str(replacement)),
                placeholder.get_conditional_body(replacement)
            )

        if not self.preview_mode:
            replaced_value = self.get_replacement(placeholder)
            if replaced_value is None and not self.is_okay_to_have_null_values(placeholder):
                raise NullValueForNonConditionalPlaceholderException
            elif replaced_value is not None:
                return self.get_replacement(placeholder)

        # TODO - Investigate why this fallback is necessary, and potentially remove
        # it to enable truly conditional placeholders.
        return self.format_match(match)

    def is_okay_to_have_null_values(self, placeholder) -> bool:
        return self.redact_missing_personalisation or placeholder.is_conditional()

    def get_replacement(self, placeholder):
        replacement = self.values.get(placeholder.name)
        if replacement is None:
            return None

        if isinstance(replacement, list):
            vals = list(filter(None, replacement))
            if not vals:
                return None
            return self.sanitizer(self.get_replacement_as_list(vals))

        return self.sanitizer(str(replacement))

    def get_replacement_as_list(self, replacement):
        if self.markdown_lists:
            return '\n\n' + '\n'.join(
                '* {}'.format(item) for item in replacement
            )
        return unescaped_formatted_list(replacement, before_each='', after_each='')

    @property
    def _raw_formatted(self):
        return re.sub(
            self.placeholder_pattern, self.format_match, self.sanitizer(self.content)
        )

    @property
    def formatted(self):
        return Markup(self._raw_formatted)

    @property
    def placeholders(self):
        return set(
            Placeholder(body) for body in re.findall(
                self.placeholder_pattern, self.content
            )
        )

    @property
    def placeholder_names(self):
        return set(placeholder.name for placeholder in self.placeholders)

    @property
    def replaced(self):
        return re.sub(
            self.placeholder_pattern, self.replace_match, self.sanitizer(self.content)
        )


class NullValueForNonConditionalPlaceholderException(Exception):
    pass

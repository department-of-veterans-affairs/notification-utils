import logging
import re
import sys
import csv
import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_number
import os
from io import StringIO
from contextlib import suppress
from functools import lru_cache
from itertools import islice
from collections import OrderedDict
from . import EMAIL_REGEX_PATTERN, hostname_part, tld_part
from notifications_utils.formatters import strip_and_remove_obscure_whitespace, strip_whitespace
from notifications_utils.template import Template
from notifications_utils.columns import Columns, Row, Cell

DEFAULT_COUNTRY_CODE = os.getenv("PHONE_COUNTRY_CODE", "1")
DEFAULT_REGION_CODE = os.getenv("PHONE_REGION_CODE", "US")
NON_GEOGRAPHIC_REGION_CODE = '001'

first_column_headings = {
    'email': ['email address'],
    'sms': ['phone number'],
    'letter': [
        'address line 1',
        'address line 2',
        'address line 3',
        'address line 4',
        'address line 5',
        'address line 6',
        'postcode',
    ],
}

optional_address_columns = {
    'address line 3',
    'address line 4',
    'address line 5',
    'address line 6',
}


class RecipientCSV():

    max_rows = 50000

    def __init__(
        self,
        file_data,
        template_type=None,
        placeholders=None,
        max_errors_shown=20,
        max_initial_rows_shown=10,
        whitelist=None,
        template=None,
        remaining_messages=sys.maxsize,
        international_sms=False,
    ):
        self.file_data = strip_whitespace(file_data, extra_characters=',')
        self.template_type = template_type
        self.placeholders = placeholders
        self.max_errors_shown = max_errors_shown
        self.max_initial_rows_shown = max_initial_rows_shown
        self.whitelist = whitelist
        self.template = template if isinstance(template, Template) else None
        self.international_sms = international_sms
        self.remaining_messages = remaining_messages
        self.rows_as_list = None

    def __len__(self):
        if not hasattr(self, '_len'):
            self._len = len(self.rows)
        return self._len

    def __getitem__(self, requested_index):
        return self.rows[requested_index]

    @property
    def whitelist(self):
        return self._whitelist

    @whitelist.setter
    def whitelist(self, value):
        try:
            self._whitelist = list(value)
        except TypeError:
            self._whitelist = []

    @property
    def placeholders(self):
        return self._placeholders

    @placeholders.setter
    def placeholders(self, value):
        try:
            self._placeholders = list(value) + self.recipient_column_headers
        except TypeError:
            self._placeholders = self.recipient_column_headers
        self.placeholders_as_column_keys = [
            Columns.make_key(placeholder)
            for placeholder in self._placeholders
        ]
        self.recipient_column_headers_as_column_keys = [
            Columns.make_key(placeholder)
            for placeholder in self.recipient_column_headers
        ]

    @property
    def template_type(self):
        return self._template_type

    @template_type.setter
    def template_type(self, value):
        self._template_type = value
        self.recipient_column_headers = first_column_headings[self.template_type]

    @property
    def has_errors(self):
        return bool(
            self.missing_column_headers
            or self.duplicate_recipient_column_headers
            or self.more_rows_than_can_send
            or self.too_many_rows
            or not self.allowed_to_send_to
            or any(self.rows_with_errors)
        )  # `or` is 3x faster than using `any()` here

    @property
    def allowed_to_send_to(self):
        if self.template_type == 'letter':
            return True
        if not self.whitelist:
            return True
        return all(
            allowed_to_send_to(row.recipient, self.whitelist)
            for row in self.rows
        )

    @property
    def rows(self):
        if self.rows_as_list is None:
            self.rows_as_list = list(self.get_rows())
        return self.rows_as_list

    @property
    def _rows(self):
        return csv.reader(
            StringIO(self.file_data.strip()),
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=True,
        )

    def get_rows(self):

        column_headers = self._raw_column_headers  # this is for caching
        length_of_column_headers = len(column_headers)

        rows_as_lists_of_columns = self._rows

        next(rows_as_lists_of_columns, None)  # skip the header row

        for index, row in enumerate(rows_as_lists_of_columns):

            output_dict = OrderedDict()

            for column_name, column_value in zip(column_headers, row):

                column_value = strip_and_remove_obscure_whitespace(column_value)

                if Columns.make_key(column_name) in self.recipient_column_headers_as_column_keys:
                    output_dict[column_name] = column_value or None
                else:
                    insert_or_append_to_dict(output_dict, column_name, column_value or None)

            length_of_row = len(row)

            if length_of_column_headers < length_of_row:
                output_dict[None] = row[length_of_column_headers:]
            elif length_of_column_headers > length_of_row:
                for key in column_headers[length_of_row:]:
                    insert_or_append_to_dict(output_dict, key, None)

            if index < self.max_rows:
                yield Row(
                    output_dict,
                    index=index,
                    error_fn=self._get_error_for_field,
                    recipient_column_headers=self.recipient_column_headers,
                    placeholders=self.placeholders_as_column_keys,
                    template=self.template,
                )
            else:
                yield None

    @property
    def more_rows_than_can_send(self):
        return len(self) > self.remaining_messages

    @property
    def too_many_rows(self):
        return len(self) > self.max_rows

    @property
    def initial_rows(self):
        return islice(self.rows, self.max_initial_rows_shown)

    @property
    def displayed_rows(self):
        if any(self.rows_with_errors) and not self.missing_column_headers:
            return self.initial_rows_with_errors
        return self.initial_rows

    def _filter_rows(self, attr):
        return (row for row in self.rows if row and getattr(row, attr))

    @property
    def rows_with_errors(self):
        return self._filter_rows('has_error')

    @property
    def rows_with_bad_recipients(self):
        return self._filter_rows('has_bad_recipient')

    @property
    def rows_with_missing_data(self):
        return self._filter_rows('has_missing_data')

    @property
    def rows_with_message_too_long(self):
        return self._filter_rows('message_too_long')

    @property
    def initial_rows_with_errors(self):
        return islice(self.rows_with_errors, self.max_errors_shown)

    @property
    def _raw_column_headers(self):
        for row in self._rows:
            return row
        return []

    @property
    def column_headers(self):
        return list(set(self._raw_column_headers))

    @property
    def column_headers_as_column_keys(self):
        return Columns.from_keys(self.column_headers).keys()

    @property
    def missing_column_headers(self):
        return set(
            key for key in self.placeholders
            if (
                Columns.make_key(key) not in self.column_headers_as_column_keys
                and not self.is_optional_address_column(key)
            )
        )

    @property
    def duplicate_recipient_column_headers(self):

        raw_recipient_column_headers = [
            Columns.make_key(column_header)
            for column_header in self._raw_column_headers
            if Columns.make_key(column_header) in self.recipient_column_headers_as_column_keys
        ]

        return set((
            column_header
            for column_header in self._raw_column_headers
            if raw_recipient_column_headers.count(Columns.make_key(column_header)) > 1
        ))

    def is_optional_address_column(self, key):
        return (
            self.template_type == 'letter'
            and Columns.make_key(key) in Columns.from_keys(optional_address_columns).keys()
        )

    @property
    def has_recipient_columns(self):
        return set(
            Columns.make_key(recipient_column)
            for recipient_column in self.recipient_column_headers
            if not self.is_optional_address_column(recipient_column)
        ) <= self.column_headers_as_column_keys

    def _get_error_for_field(self, key, value):  # noqa: C901

        if self.is_optional_address_column(key):
            return

        if Columns.make_key(key) in self.recipient_column_headers_as_column_keys:
            if value in [None, ''] or isinstance(value, list):
                if self.duplicate_recipient_column_headers:
                    return None
                else:
                    return Cell.missing_field_error
            try:
                validate_recipient(
                    value,
                    self.template_type,
                    column=key,
                )
            except (InvalidEmailError, InvalidPhoneError, InvalidAddressError) as error:
                return str(error)

        if Columns.make_key(key) not in self.placeholders_as_column_keys:
            return

        if value in [None, '']:
            return Cell.missing_field_error


class InvalidEmailError(Exception):

    def __init__(self, message=None):
        super().__init__(message or 'Not a valid email address')


class InvalidPhoneError(Exception):

    def __init__(self, message=None):
        super().__init__(message or 'Not a valid number')


class InvalidAddressError(InvalidEmailError):
    pass


class ValidatedPhoneNumber:
    def __init__(self, number: str):
        # raises InvalidPhoneNumber if letters present
        _reject_vanity_number(number)
        try:
            self._parsed: phonenumbers.PhoneNumber = phonenumbers.parse(number, DEFAULT_REGION_CODE)
        except (TypeError, phonenumbers.NumberParseException):
            raise InvalidPhoneError('Not a possible number')
        if self.region_code == NON_GEOGRAPHIC_REGION_CODE:
            # Country prefix/code maps to a non-geographic region like shared-cost or a satellite phone
            # Note that phonenumbers returns '001' to indicate the non-geographic regions.
            # This is the exception to all other region codes which are a two letter string like 'US' or 'CA'
            raise InvalidPhoneError('Not a valid country prefix')
        if not phonenumbers.is_valid_number(self._parsed):
            raise InvalidPhoneError('Not a valid number')

    @property
    def formatted(self) -> str:
        """Phone number as E164 formatted string."""
        return phonenumbers.format_number(self._parsed, phonenumbers.PhoneNumberFormat.E164)

    @property
    def international(self) -> bool:
        """Is phone number international."""
        return self.region_code != DEFAULT_REGION_CODE

    @property
    def country_code(self) -> str:
        """Country code of phone number as a string."""
        return str(self._parsed.country_code)

    @property
    def region_code(self) -> str:
        """Region code of phone number."""
        return region_code_for_number(self._parsed)

    @property
    def billable_units(self) -> int:
        """Billable units for phone number referenced using country code.

        Previously looked up by combination of country code and NSN and in the billing rates and used as a multiplier.
        Billing rates yaml file is incomplete and/or out of date.

        INTERNATIONAL_BILLING_RATES[billing_prefix]['billable_units']

        Note: AWS returns a total_cost_millicents so returning a hardcoded 1.
        """
        return 1


def _reject_vanity_number(number: str) -> None:
    """Raise InvalidPhoneError is number string has alpha characters."""
    _number = re.sub(r'\s*(x|ext|extension)\s*\d+$', '', number, flags=re.IGNORECASE).strip()

    # do not allow letters in phone number (vanity)
    if re.search(r'[A-Za-z]', _number) is not None:
        raise InvalidPhoneError('Phone numbers must not contain letters')


def validate_phone_number(number, column=None) -> str:
    """Wrapper function to retain compatability with validate_recipient."""
    return ValidatedPhoneNumber(number).formatted


def try_validate_and_format_phone_number(number, log_msg=None):
    """
    For use in places where you shouldn't error if the phone number is invalid
      - for example if firetext pass us something in

    Note: Caller is responsible for adding qualifiers to the log message
    """
    try:
        return ValidatedPhoneNumber(number).formatted
    except InvalidPhoneError:
        if log_msg:
            logging.exception(log_msg)
        return number


def validate_email_address(email_address, column=None):  # noqa (C901 too complex)
    # almost exactly the same as by https://github.com/wtforms/wtforms/blob/master/wtforms/validators.py,
    # with minor tweaks for SES compatibility - to avoid complications we are a lot stricter with the local part
    # than neccessary - we don't allow any double quotes or semicolons to prevent SES Technical Failures
    email_address = strip_and_remove_obscure_whitespace(email_address)
    match = re.match(EMAIL_REGEX_PATTERN, email_address)

    # not an email
    if not match:
        raise InvalidEmailError

    if len(email_address) > 320:
        raise InvalidEmailError

    # don't allow consecutive periods in either part
    if '..' in email_address:
        raise InvalidEmailError

    hostname = match.group(1)

    # idna = "Internationalized domain name" - this encode/decode cycle converts unicode into its accurate ascii
    # representation as the web uses. '例え.テスト'.encode('idna') == b'xn--r8jz45g.xn--zckzah'
    try:
        hostname = hostname.encode('idna').decode('ascii')
    except UnicodeError:
        raise InvalidEmailError

    parts = hostname.split('.')

    if len(hostname) > 253 or len(parts) < 2:
        raise InvalidEmailError

    for part in parts:
        if not part or len(part) > 63 or not hostname_part.match(part):
            raise InvalidEmailError

    # if the part after the last . is not a valid TLD then bail out
    if not tld_part.match(parts[-1]):
        raise InvalidEmailError

    return email_address


def format_email_address(email_address):
    return strip_and_remove_obscure_whitespace(email_address.lower())


def validate_and_format_email_address(email_address):
    return format_email_address(validate_email_address(email_address))


def validate_address(address_line, column):
    if Columns.make_key(column) in Columns.from_keys(optional_address_columns).keys():
        return address_line
    if Columns.make_key(column) not in Columns.from_keys(first_column_headings['letter']).keys():
        raise TypeError
    if not address_line or not strip_whitespace(address_line):
        raise InvalidAddressError('Missing')
    return address_line


def validate_recipient(recipient, template_type, column=None):
    return {
        'email': validate_email_address,
        'sms': validate_phone_number,
        'letter': validate_address,
    }[template_type](recipient, column)


@lru_cache(maxsize=32, typed=False)
def format_recipient(recipient):
    if not isinstance(recipient, str):
        return ''
    with suppress(InvalidPhoneError):
        return ValidatedPhoneNumber(recipient).formatted
    with suppress(InvalidEmailError):
        return validate_and_format_email_address(recipient)
    return recipient


def allowed_to_send_to(recipient, whitelist):
    return format_recipient(recipient) in [
        format_recipient(recipient) for recipient in whitelist
    ]


def insert_or_append_to_dict(dict_, key, value):
    if dict_.get(key):
        if isinstance(dict_[key], list):
            dict_[key].append(value)
        else:
            dict_[key] = [dict_[key], value]
    else:
        dict_.update({key: value})

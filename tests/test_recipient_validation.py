import pytest

from functools import partial

from notifications_utils.recipients import (
    ValidatedPhoneNumber,
    InvalidPhoneError,
    validate_email_address,
    InvalidEmailError,
    allowed_to_send_to,
    InvalidAddressError,
    validate_recipient,
    format_recipient,
    try_validate_and_format_phone_number
)


valid_local_phone_numbers = [
    '6502532222',
    '+16502532222',
    '+1 650-253-2222',
    '650-253-2222',
    '16502532222',
    '1 6502532222',
]


valid_international_phone_numbers = [
    '+79587714230',  # Russia
    '+2302086859',  # Mauritius,
]


valid_phone_numbers = valid_local_phone_numbers + valid_international_phone_numbers


invalid_local_phone_numbers = sum([
    [
        (phone_number, error) for phone_number in group
    ] for error, group in [
        ('Not a valid number', (
            '712345678910',
            '0712345678910',
            '0044712345678910',
            '0044712345678910',
            '+44 (0)7123 456 789 10',
        )),
        ('Not a valid number', (
            '0712345678',
            '004471234567',
            '00447123456',
            '+44 (0)7123 456 78',
        )),
        ('Not a valid number', (
            '08081 570364',
            '0117 496 0860',
            '020 7946 0991',
        )),
        ('Not a valid number', (
            '07890x32109',
            '07123 456789...',
            '07123 ☟☜⬇⬆☞☝',
            '07123☟☜⬇⬆☞☝',
        ))
    ]
], [])


invalid_phone_numbers = [
    ('+21 4321 0987', 'Not a possible number'),  # Invalid country prefix, does not parse
    ('+681 4321 0987', 'Not a valid country prefix'),  # Invalid country prefix, parses
    ('+003997 1234 7890', 'Not a possible number'),
    ('ALPHANUM3R1C', 'Phone numbers must not contain letters'),
    ('800000000000', 'Not a valid number'),
    ('1234567', 'Not a valid number'),
    ('+682 1234', 'Not a valid number'),  # Cook Islands phone numbers can be 5 digits
    ('+17553927664', 'Not a valid number'),
]


valid_email_addresses = (
    'email@domain.com',
    'email@domain.COM',
    'firstname.lastname@domain.com',
    'firstname.o\'lastname@domain.com',
    'email@subdomain.domain.com',
    'firstname+lastname@domain.com',
    '1234567890@domain.com',
    'email@domain-one.com',
    '_______@domain.com',
    'email@domain.name',
    'email@domain.superlongtld',
    'email@domain.co.jp',
    'firstname-lastname@domain.com',
    'info@german-financial-services.vermögensberatung',
    'info@german-financial-services.reallylongarbitrarytldthatiswaytoohugejustincase',
    'japanese-info@例え.テスト',
)
invalid_email_addresses = (
    'email@123.123.123.123',
    'email@[123.123.123.123]',
    'plainaddress',
    '@no-local-part.com',
    'Outlook Contact <outlook-contact@domain.com>',
    'no-at.domain.com',
    'no-tld@domain',
    ';beginning-semicolon@domain.co.uk',
    'middle-semicolon@domain.co;uk',
    'trailing-semicolon@domain.com;',
    '"email+leading-quotes@domain.com',
    'email+middle"-quotes@domain.com',
    '"quoted-local-part"@domain.com',
    '"quoted@domain.com"',
    'lots-of-dots@domain..gov..uk',
    'two-dots..in-local@domain.com',
    'multiple@domains@domain.com',
    'spaces in local@domain.com',
    'spaces-in-domain@dom ain.com',
    'underscores-in-domain@dom_ain.com',
    'pipe-in-domain@example.com|gov.uk',
    'comma,in-local@gov.uk',
    'comma-in-domain@domain,gov.uk',
    'pound-sign-in-local£@domain.com',
    'local-with-’-apostrophe@domain.com',
    'local-with-”-quotes@domain.com',
    'domain-starts-with-a-dot@.domain.com',
    'brackets(in)local@domain.com',
    'email-too-long-{}@example.com'.format('a' * 320),
)


@pytest.mark.parametrize("phone_number, international, country_code, region_code, billable_units", [
    ('+447900900123', True, '44', 'GB', 1),     # UK
    ('+20-12-1234-1234', True, '20', 'EG', 3),  # Egypt
    ('+201212341234', True, '20', 'EG', 3),     # Egypt
    ('+79587714230', True, '7', 'RU', 1),       # Russia
    ('1-202-555-0104', False, '1', 'US', 1),    # USA
    ('+2302086859', True, '230', 'MU', 2),      # Mauritius
])
def test_get_international_info(
    phone_number: str,
    international: bool,
    country_code: str,
    region_code: str,
    billable_units: int,
):
    validated = ValidatedPhoneNumber(phone_number)
    assert validated.international == international
    assert validated.country_code == country_code
    assert validated.billable_units == billable_units
    assert validated.region_code == region_code


@pytest.mark.parametrize("phone_number", valid_local_phone_numbers)
@pytest.mark.parametrize("validator", [
    partial(validate_recipient, template_type='sms'),
    ValidatedPhoneNumber,
])
def test_phone_number_accepts_valid_values(validator, phone_number):
    try:
        validator(phone_number)
    except InvalidPhoneError:
        pytest.fail('Unexpected InvalidPhoneError')


@pytest.mark.parametrize('phone, error_msg', [
    ('07";DROP TABLE;', 'Phone numbers must not contain letters'),
    ('416-234-8976;416-235-8976', 'Not a possible number'),
])
def test_phone_with_invalid_semicolon_usage(phone, error_msg):
    with pytest.raises(InvalidPhoneError) as e:
        ValidatedPhoneNumber(phone)
    assert error_msg == str(e.value)


@pytest.mark.parametrize('phone', [
    '1800ABDEFGH',
    '1-800-ABC-DEFG',
])
def test_phone_with_vanity_raises(phone):
    with pytest.raises(InvalidPhoneError) as e:
        ValidatedPhoneNumber(phone)
    assert "Phone numbers must not contain letters" == str(e.value)


@pytest.mark.parametrize("phone_number", valid_phone_numbers)
@pytest.mark.parametrize("validator", [
    partial(validate_recipient, template_type='sms'),
    ValidatedPhoneNumber,
])
def test_phone_number_accepts_valid_international_values(validator, phone_number):
    try:
        validator(phone_number)
    except InvalidPhoneError:
        pytest.fail('Unexpected InvalidPhoneError')


@pytest.mark.parametrize("phone_number", valid_local_phone_numbers)
def test_valid_local_phone_number_can_be_formatted_consistently(phone_number):
    assert ValidatedPhoneNumber(phone_number).formatted == '+16502532222'


@pytest.mark.parametrize("phone_number, expected_formatted", [
    ('+79587714230', '+79587714230'),
    ('1-202-555-0104', '+12025550104'),
    ('+12025550104', '+12025550104'),
    ('+2302086859', '+2302086859'),
])
def test_valid_international_phone_number_can_be_formatted_consistently(phone_number, expected_formatted):
    assert ValidatedPhoneNumber(phone_number).formatted == expected_formatted


@pytest.mark.parametrize("phone_number, error_message", invalid_local_phone_numbers)
@pytest.mark.parametrize("validator", [
    partial(validate_recipient, template_type='sms'),
    ValidatedPhoneNumber,
])
def test_phone_number_rejects_invalid_values(validator, phone_number, error_message):
    with pytest.raises(InvalidPhoneError) as e:
        validator(phone_number)
    assert error_message == str(e.value)


@pytest.mark.parametrize("phone_number, error_message", invalid_phone_numbers)
@pytest.mark.parametrize("validator", [
    partial(validate_recipient, template_type='sms'),
    ValidatedPhoneNumber,
])
def test_phone_number_rejects_invalid_international_values(validator, phone_number, error_message):
    with pytest.raises(InvalidPhoneError) as e:
        validator(phone_number)
    assert error_message == str(e.value)


@pytest.mark.parametrize("email_address", valid_email_addresses)
def test_validate_email_address_accepts_valid(email_address):
    try:
        assert validate_email_address(email_address) == email_address
    except InvalidEmailError:
        pytest.fail('Unexpected InvalidEmailError')


@pytest.mark.parametrize('email', [
    ' email@domain.com ',
    '\temail@domain.com',
    '\temail@domain.com\n',
    '\u200Bemail@domain.com\u200B',
])
def test_validate_email_address_strips_whitespace(email):
    assert validate_email_address(email) == 'email@domain.com'


@pytest.mark.parametrize("email_address", invalid_email_addresses)
def test_validate_email_address_raises_for_invalid(email_address):
    with pytest.raises(InvalidEmailError) as e:
        validate_email_address(email_address)
    assert str(e.value) == 'Not a valid email address'


@pytest.mark.parametrize('column', [
    'address_line_1', 'AddressLine1',
    'postcode', 'Postcode'
])
@pytest.mark.parametrize('contents', [
    '', ' ', None
])
def test_validate_address_raises_for_missing_required_columns(column, contents):
    with pytest.raises(InvalidAddressError) as e:
        validate_recipient(contents, 'letter', column=column)
    assert 'Missing' == str(e.value)


@pytest.mark.parametrize('column', [
    'address_line_3',
    'address_line_4',
    'address_line_5',
    'address_line_6',
])
def test_validate_address_doesnt_raise_for_missing_optional_columns(column):
    assert validate_recipient('', 'letter', column=column) == ''


def test_validate_address_raises_for_wrong_column():
    with pytest.raises(TypeError):
        validate_recipient('any', 'letter', column='email address')


@pytest.mark.parametrize('column', [
    'address_line_1',
    'address_line_2',
    'address_line_3',
    'address_line_4',
    'address_line_5',
    'postcode',
])
def test_validate_address_allows_any_non_empty_value(column):
    assert validate_recipient('any', 'letter', column=column) == 'any'


@pytest.mark.parametrize('column', [
    'address_line_1',
    'address_line_2',
    'address_line_3',
    'address_line_4',
    'address_line_5',
    'address_line_6',
    'postcode',
])
def test_non_ascii_address_line_is_fine(column):
    valid_address = u'\u041F\u0435\u0442\u044F'
    assert validate_recipient(
        valid_address, 'letter', column=column
    ) == valid_address


def test_valid_address_line_does_not_raise_error():
    invalid_address = u'Fran\u00e7oise'
    assert validate_recipient(invalid_address, 'letter', column='address_line_1')


@pytest.mark.parametrize("phone_number", valid_local_phone_numbers)
def test_validates_against_whitelist_of_phone_numbers(phone_number):
    assert allowed_to_send_to(phone_number, ['6502532222', '07700900460', 'test@example.com'])
    assert not allowed_to_send_to(phone_number, ['07700900460', '07700900461', 'test@example.com'])


@pytest.mark.parametrize("email_address", valid_email_addresses)
def test_validates_against_whitelist_of_email_addresses(email_address):
    assert not allowed_to_send_to(email_address, ['very_special_and_unique@example.com'])


@pytest.mark.parametrize("recipient, expected_formatted", [
    (True, ''),
    (False, ''),
    (0, ''),
    (0.1, ''),
    (None, ''),
    ('foo', 'foo'),
    ('TeSt@ExAmPl3.com', 'test@exampl3.com'),
    ('+14407900 900 123', '+14407900 900 123'),  # invalid number
    ('+1 800 555 5555', '+18005555555'),
])
def test_format_recipient(recipient, expected_formatted):
    assert format_recipient(recipient) == expected_formatted


def test_try_format_recipient_doesnt_throw():
    assert try_validate_and_format_phone_number('ALPHANUM3R1C', log_msg="Log this.") == 'ALPHANUM3R1C'

import pytest
from .context import api


# fields object to validate
test_char_field = api.CharField()
test_email_field = api.EmailField()              # at least have @. But here is more rigid reqs. It Should be like email
test_phone_field = api.PhoneField()              # begins with 7. Have 11 digits
test_date_field = api.DateField()                # DD.MM.YYYY
test_bday_field = api.BirthDayField()            # DD.MM.YYYY no more than 70 years from current year
test_gender_field = api.GenderField()            # should be in [1,2,3]
test_argument_field = api.ArgumentsField()       # should be dict
test_client_id_field = api.ClientIDsField()      # should be a list


def validate_field_generic(input_data, should_validate, test_field):
    if not should_validate:
        with pytest.raises(ValueError):
            test_field.validate(input_data)
    else:
        assert test_field.validate(input_data)is None


# CHAR FIELDS
@pytest.mark.parametrize("test_char_field", [test_char_field], ids=['test_char_field'])
@pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", True),
    ("", True),
    (-1, False)
    ],
    ids=["number", "text", "empty", "-1"])
def test_char_field(input_data, should_validate, test_char_field):
    validate_field_generic(input_data, should_validate, test_char_field)


# EMAIL FIELDS
@pytest.mark.parametrize("test_email_field", [test_email_field], ids=['test_email_field'])
@pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    (-1, False),
    ("haha@hoho", False),
    ("hello@world.ru", True)
    ],
    ids=["number", "text", "empty", "-1", "string mimic email", "good email"])
def test_char_field(input_data, should_validate, test_email_field):
    validate_field_generic(input_data, should_validate, test_email_field)


# PHONE FIELDS
@pytest.mark.parametrize("test_phone_field", [test_phone_field], ids=['test_phone_field'])
@pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    (-1, False),
    ("7123456789", False),
    ("81234567890", False),
    ("7I234567890", False),
    ("71234567890", True),
    ],
    ids=["number", "text", "empty", "-1", "begins_with7_10_digits",
         "not_begins_with7_11_digits", "contain_chars", "valid_phone"])
def test_char_field(input_data, should_validate, test_phone_field):
    validate_field_generic(input_data, should_validate, test_phone_field)

# DATE FIELDS
@pytest.mark.parametrize("test_date_field", [test_date_field], ids=['test_date_field'])
@pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    (-1, False),
    ([1, 2, 3], False),
    ("2001.06.15", False),
    ("05.10.99", False),
    ("22.11.1990", True),
    ],
    ids=["number", "text", "empty", "-1", "list",
         "format YYYY.MM.DD", "format DD.MM.YY", "valid_date"])
def test_date_field(input_data, should_validate, test_date_field):
    validate_field_generic(input_data, should_validate, test_date_field)

# BIRTHDAY FIELDS
@ pytest.mark.parametrize("test_bday_field", [test_bday_field], ids=['test_bday_field'])
@ pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    (-1, False),
    ([1, 2, 3], False),
    ("2001.06.15", False),
    ("05.10.99", False),
    ("22.11.1948", True),
    ("22.11.1947", True),
    ("22.11.1946", False)
    ],
    ids=["number", "text", "empty", "-1", "list",
          "format YYYY.MM.DD", "format DD.MM.YY", "69 years from current", "70 years from current",
          "71 years from current"])
def test_bday_field(input_data, should_validate, test_bday_field):
    validate_field_generic(input_data, should_validate, test_bday_field)


# GENDER FIELDS
@ pytest.mark.parametrize("test_gender_field", [test_gender_field], ids=['test_gender_field'])
@ pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    (-1, False),
    ([1, 2], False),
    (0, True),
    (1, True),
    (2, True),
    (3, False),
    ("1", False)
    ],
    ids=["number 555", "text", "empty", "-1", "list", "number 0", "number 1", "number 2", "number 3", "char 1"])
def test_gender_field(input_data, should_validate, test_gender_field):
    validate_field_generic(input_data, should_validate, test_gender_field)


# ARGUMENT FIELDS
@pytest.mark.parametrize("test_char_field", [test_argument_field], ids=['test_argument_field'])
@pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    ([1, 2, 3], False),
    ({}, True),
    ({1: "ff", 2: "sss"}, True)
    ],
    ids=["number", "text", "empty", "list", "empty dict", "non empty dict"])
def test_arguments_field(input_data, should_validate, test_char_field):
    validate_field_generic(input_data, should_validate, test_char_field)

# CLIENT ID FIELDS
@pytest.mark.parametrize("test_client_id_field", [test_client_id_field], ids=['test_client_id_field'])
@pytest.mark.parametrize(("input_data", "should_validate"), [
    (555, False),
    ("text", False),
    ("", True),
    ([1, 2, 3], True),
    ([], True),
    ({1: "ff", 2: "sss"}, False)
    ],
    ids=["number", "text", "empty", "list", "empty list", "non empty dict"])
def test_client_id_field(input_data, should_validate, test_client_id_field):
    validate_field_generic(input_data, should_validate, test_client_id_field)

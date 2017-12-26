import pytest
from .context import api


# CHAR FIELDS
@pytest.mark.parametrize("input_data", ["text", ""], ids=["text", "empty"])
def test_char_field_good_input(input_data):
    test_char_field = api.CharField()
    assert test_char_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, -1], ids=["number", "-1"])
def test_char_field_bad_input(input_data):
    test_char_field = api.CharField()
    with pytest.raises(ValueError):
        test_char_field.validate(input_data)


# EMAIL FIELDS
@pytest.mark.parametrize("input_data", ["", "hello@world.ru"], ids=["empty", "good email"])
def test_email_field_good_input(input_data):
    test_email_field = api.EmailField()
    assert test_email_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text",-1,"haha@hoho"], ids=["number", "text", "-1", "string mimic email"])
def test_email_field_bad_input(input_data):
    test_email_field = api.EmailField()
    with pytest.raises(ValueError):
        test_email_field.validate(input_data)


# PHONE FIELDS
@pytest.mark.parametrize("input_data", ["", "71234567890", 71234567890], ids=["empty", "valid_phone_text",
                                                                              "valid_phone_number" ])
def test_phone_field_good_input(input_data):
    test_phone_field = api.PhoneField()
    assert test_phone_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text", -1, "7123456789", "81234567890", "7I234567890"],
                         ids=["number", "text", "-1", "begins_with7_10_digits", "not_begins_with7_11_digits",
                              "contain_chars"])
def test_phone_field_bad_input(input_data):
    test_phone_field = api.PhoneField()
    with pytest.raises(ValueError):
        test_phone_field.validate(input_data)


# DATE FIELDS
@pytest.mark.parametrize("input_data", ["", "22.11.1990"], ids=[ "empty", "valid_date"])
def test_date_field_good_input(input_data):
    test_date_field = api.DateField()
    assert test_date_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text", -1, [1, 2, 3], "2001.06.15", "05.10.99"],
                         ids=["number", "text", "-1", "list", "format YYYY.MM.DD", "format DD.MM.YY"])
def test_date_field_bad_input(input_data):
    test_date_field = api.DateField()
    with pytest.raises(ValueError):
        test_date_field.validate(input_data)

# BIRTHDAY FIELDS
@pytest.mark.parametrize("input_data", ["", "22.11.1948", "22.11.1947"],
                         ids=["empty","69 years from current", "70 years from current"])
def test_bday_field_good_input(input_data):
    test_bday_field = api.BirthDayField()
    assert test_bday_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text", -1, [1, 2, 3], "2001.06.15", "05.10.99", "22.11.1946"],
                         ids=["number", "text", "-1", "list", "format YYYY.MM.DD", "format DD.MM.YY",
                              "71 years from current"])
def test_bday_field_bad_input(input_data):
    test_bday_field = api.BirthDayField()
    with pytest.raises(ValueError):
        test_bday_field.validate(input_data)


# GENDER FIELDS
@pytest.mark.parametrize("input_data", ["", 0, 1, 2], ids=["empty", "number 0", "number 1", "number 2"])
def test_gender_field_good_input(input_data):
    test_gender_field = api.GenderField()
    assert test_gender_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text", -1, [1, 2], 3, "1"],
                         ids=["number 555", "text", "-1", "list", "number 3", "char 1"])
def test_gender_field_bad_input(input_data):
    test_gender_field = api.GenderField()
    with pytest.raises(ValueError):
        test_gender_field.validate(input_data)


# ARGUMENT FIELDS
@pytest.mark.parametrize("input_data", ["", {}, {1: "ff", 2: "sss"}], ids=["empty", "empty dict", "non empty dict"])
def test_arguments_field_good_input(input_data):
    test_argument_field = api.ArgumentsField()
    assert test_argument_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text", [1, 2, 3]], ids=["number", "text", "list"])
def test_arguments_field_bad_input(input_data):
    test_argument_field = api.ArgumentsField()
    with pytest.raises(ValueError):
        test_argument_field.validate(input_data)


# CLIENT ID FIELDS
@pytest.mark.parametrize("input_data", ["", [1, 2, 3], []], ids=["empty", "list", "empty list"])
def test_client_id_field_good_input(input_data):
    test_client_id_field = api.ClientIDsField()
    assert test_client_id_field.validate(input_data) is None


@pytest.mark.parametrize("input_data", [555, "text", {1: "ff", 2: "sss"}], ids=["number", "text", "non empty dict"])
def test_client_id_field_bad_input(input_data):
    test_client_id_field = api.ClientIDsField()
    with pytest.raises(ValueError):
        test_client_id_field.validate(input_data)

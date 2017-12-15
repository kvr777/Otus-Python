#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
from scoring import get_score, get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

# These values, if given to validate(), will trigger the self.nullable check.
EMPTY_VALUES = (None, '', [], (), {})


class Field(metaclass=ABCMeta):
    """
    Basic field class with function pattern for child field classes.
    """

    @abstractmethod
    def __init__(self, label=None, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    @abstractmethod
    def validate(self, label):
        raise NotImplementedError


class CharField(Field):
    """
    Field for string type characters
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        if label not in list(EMPTY_VALUES):
            if not isinstance(label, str):
                raise ValueError("CharField accepts only string type")


class ArgumentsField(Field):
    """
        Field to accept dict with arguments
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        if label not in list(EMPTY_VALUES):
            if not isinstance(label, dict):
                raise ValueError("ArgumentsField accepts only dict type")


class EmailField(CharField):
    """
        Field for e-mail. Child class from CharField
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        super().validate(label)
        if label not in list(EMPTY_VALUES):
            email_regex = re.compile(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")
            if not email_regex.match(label):
                raise ValueError("Here is not valid e-mail address")


class PhoneField(Field):
    """
    Field for phone. Should contains 11 digits and begin with 7
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        if label not in list(EMPTY_VALUES):
            if not (len(str(label)) == 11 and str(label).startswith('7') and str(label).isdigit()):
                raise ValueError("phone number should have 11 digits and start with 7")


class DateField(Field):
    """
    Field for date in format DD.MM.YYY
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        if label not in list(EMPTY_VALUES):
            try:
                datetime.datetime.strptime(str(label), '%d.%m.%Y')
            except ValueError:
                raise ValueError("Incorrect date format, should be DD-MM-YYYY")


class BirthDayField(DateField):
    """
    Field for birthday in format DD.MM.YYY and year not older than 70 years from current year
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        super().validate(label)
        if label not in list(EMPTY_VALUES):
            current_date = datetime.datetime.now()
            converted_birthday = datetime.datetime.strptime(str(label), '%d.%m.%Y')

            if (current_date.year - converted_birthday.year) > 70:
                print(current_date.year, converted_birthday.year)
                raise ValueError("Birthday year cannot be higher than 70 years from now")


class GenderField(Field):
    """
    If this field is not empty it could accept only 0, 1,2
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        if label not in list(EMPTY_VALUES):
            if label not in [0, 1, 2]:
                raise ValueError("Incorrect value for gender field")


class ClientIDsField(Field):
    """
    This field should be a list
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, label):
        if label not in list(EMPTY_VALUES):
            if not isinstance(label, list):
                raise ValueError("Client Ids should be a list")


class DeclarativeFieldsMetaclass(type):
    """
    Metaclass that collects Fields declared on the base classes and check them.
    """
    def __new__(mcs, name, bases, attrs):
        # Collect fields from current class.
        all_fields = []
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                all_fields.append((key, value))
        new_class = super(DeclarativeFieldsMetaclass, mcs).__new__(mcs, name, bases, attrs)
        new_class.all_fields = all_fields
        return new_class


class RequestProcessor(metaclass=DeclarativeFieldsMetaclass):
    """
    This class accepts dict with argument values for fields, set values to fields and stores names fields that
    are not null
    Then validate function checks all values passed by init function and return dict with all errors that was discovered

    """
    def __init__(self, **passed_dict):
        non_empty_fields = []
        for field, value in list(passed_dict.items()):
            for (cls_fld_name, cls_fld_value) in self.all_fields:
                if cls_fld_name == field:
                    cls_fld_value.label = value
            if value not in list(EMPTY_VALUES):
                non_empty_fields.append(field)
        self.non_empty_fields = non_empty_fields

    def validate(self):
        error_dict = []
        for (cls_fld_name, cls_fld_value) in self.all_fields:
            if cls_fld_value.label in list(EMPTY_VALUES) and not cls_fld_value.nullable:
                error_dict.append((cls_fld_name, "This field cannot be empty"))
            if cls_fld_value.required and not hasattr(cls_fld_value, 'label'):
                error_dict.append((cls_fld_name, "This field is required"))
            if hasattr(cls_fld_value, 'label'):
                try:
                    cls_fld_value.validate(cls_fld_value.label)
                except Exception as e:
                    error_dict.append((cls_fld_name, str(e)))

        return error_dict


class ClientsInterestsRequest(RequestProcessor):
    """
    Here we initiate and validate the arguments passed by clients_interests request
    with help of get_interests func we return interest dict
    """

    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self):
        return super().validate()

    def get_interests(self, interest_list):
        response_dict = {}
        for client in interest_list:
            response_dict[client] = get_interests(store=None, cid=client)
        return response_dict


class OnlineScoreRequest(RequestProcessor):
    """
    Here we initiate and validate the arguments passed by online_score request.
    validate func get dict with general validation and do validation that is specific for online_score request
    """
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self):
        has_combo = False
        basic_error_dict = super().validate()
        required_combos = [['email', 'phone'], ['first_name', 'last_name'], ['gender', 'birthday']]
        for combo in required_combos:
            if set(combo).issubset(self.non_empty_fields):
                has_combo = True
        if not has_combo:
            basic_error_dict.append(('multiple fields', 'You need to fill at least one combination '
                                                        'of the following fields: email-phone, '
                                                        'first_name-last_name, gender-birthday'))
            return basic_error_dict


class MethodRequest(RequestProcessor):
    """
    Here we initiate and validate the all arguments passed by POST request.
    is_admin property check and store the boolean which indicate does it admin login or not
    """

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        for (cls_fld_name, cls_fld_value) in self.all_fields:
            if cls_fld_name == 'login':
                return cls_fld_value.label == ADMIN_LOGIN


def check_auth(request):
    if request['login'] == ADMIN_LOGIN:
        code_for_hash = (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')
        digest = hashlib.sha512(code_for_hash).hexdigest()
        digest = request['token']
    else:
        code_for_hash = (request['account'] + request['login'] + SALT).encode('utf-8')
        digest = hashlib.sha512(code_for_hash).hexdigest()
        digest = request['token']
    if digest == request['token']:
        return True
    return False


def method_handler(request, ctx, store):
    # pass and validate request parameters
    body_request = request['body']
    main_request = MethodRequest(**body_request)
    main_error_dict = main_request.validate()
    if main_error_dict not in list(EMPTY_VALUES):
        return main_error_dict, INVALID_REQUEST

    # if token is invalid, return Forbidden status
    if not check_auth(body_request):
        return "Forbidden", FORBIDDEN

    # process online_score method
    if request['body']['method'] == 'online_score':
        os_request = OnlineScoreRequest(**request['body']['arguments'])
        error_dict = os_request.validate()
        if error_dict in list(EMPTY_VALUES):
            ctx["has"] = os_request.non_empty_fields
            score_value = 43 if main_request.is_admin else get_score(store=None, **request['body']['arguments'])
            return {"score": score_value}, OK
        else:
            return error_dict, INVALID_REQUEST

    # process client_interest method
    elif request['body']['method'] == 'clients_interests':
        os_request = ClientsInterestsRequest(**request['body']['arguments'])
        error_dict = os_request.validate()
        if error_dict in list(EMPTY_VALUES):
            ctx["nclients"] = len(request['body']['arguments']["client_ids"])

            return os_request.get_interests(request['body']['arguments']["client_ids"]), OK
        else:
            return error_dict, INVALID_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string.decode('utf-8'), context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        output = json.dumps(r)
        self.wfile.write(output.encode('utf-8'))
        return

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=None,
                        # filename=opts.log,
                        level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

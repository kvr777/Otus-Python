from .context import api
import json
import io
import hashlib
import datetime
import pytest


def gen_good_auth(request_body):
    if request_body['login'] == api.ADMIN_LOGIN:
        code_for_hash = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()
    else:
        code_for_hash = (request_body['account'] + request_body['login'] + api.SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()


class MockedHttpHandler(api.MainHTTPHandler):

    def __init__(self, request, path):
        self.client_address = ""
        self.server = ""
        try:
            request['token'] = gen_good_auth(request)
        except:
            pass
        self.rfile = io.BytesIO(json.dumps(request).encode('utf-8'))
        self.headers = {'Content-Type': 'application/json',}
        self.headers['Content-Length'] = int(len(str(request)))
        self.wfile = io.BytesIO()
        self.client_address = ('0.0.0.0', 50631)
        self.command = 'POST'
        self.request_version = 'HTTP/1.1'
        self.path = path #'/method/'
        self.requestline = self.command+self.path+self.request_version #'POST /method/ HTTP/1.1'
        self.close_connection = True

    def get_request_id(self, headers):
        api.MainHTTPHandler.get_request_id(self, headers)

    def send_response(self, code, message=None):
        api.MainHTTPHandler.send_response(self, code, message=None)

    def send_header(self, keyword, value):
        api.MainHTTPHandler.send_header(self, keyword, value)


    def end_headers(self):
        api.MainHTTPHandler.end_headers(self)

    def do_POST(self):
        api.MainHTTPHandler.do_POST(self)
        output = self.wfile.getvalue()
        return output.decode('utf-8').split()[1]




@pytest.mark.parametrize(("request_body", "path"),
                         [({"account": "hornshoofs", "login": "hf","method": "online_score", "token": "",
                           "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru",
                                         "first_name": "stanislav", "last_name": "stupnikov",
                                         "birthday": "01.01.1990", "gender": 1}}, '/method/')],
                         ids=['valid_request-valid_path'])
def test_http_handler_valid_request(request_body, path):
    response = MockedHttpHandler(request_body, path).do_POST()
    assert int(response) == 200


@pytest.mark.parametrize(("request_body", "path"),
                         [({"account": "hornshoofs", "login": "hf","method": "online_score", "token": "",
                           "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru",
                                         "first_name": "stanislav", "last_name": "stupnikov",
                                         "birthday": "01.01.1990", "gender": 1}}, '/met/')],
                         ids=['valid_request-not_valid_path'])
def test_http_handler_invalid_path(request_body, path):
    response = MockedHttpHandler(request_body, path).do_POST()
    assert int(response) == 404


@pytest.mark.parametrize(("request_body", "path"),
                         [({"account": "hornshoofs", "login": "hf","method": "online_score", "token": "",
                           "arguments": {"pne": "79175002040", "email": "stupnikov@otus.ru",
                                         "first_name": "stanislav", "last_name": "stupnikov",
                                         "birthday": "01.01.1990", "gender": 1}}, '/method/')],
                         ids=['pne instead of phone in body field'])
def test_http_handler_internal_error(request_body, path):
    response = MockedHttpHandler(request_body, path).do_POST()
    assert int(response) == 500


@pytest.mark.parametrize(("request_body", "path"),
                         [({'"account"': "hornshoofs", "login": "hf","method": "online_score", "token": "",
                           "arguments": {"pne": "79175002040", "email": "stupnikov@otus.ru",
                                         "first_name": "stanislav", "last_name": "stupnikov",
                                         "birthday": "01.01.1990", "gender": 1}}, '/method/')],
                         ids=['account_field_with_excessive_quotes'])
def test_http_handler_bad_request(request_body, path):
    response = MockedHttpHandler(request_body, path).do_POST()
    assert int(response) == 400

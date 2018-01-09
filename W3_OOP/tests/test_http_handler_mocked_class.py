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

    def __init__(self):
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()
        self.headers = {}
        self.responses = {'code': None, 'headers':{}}

    def send_response(self, code):
        self.responses['code'] = code

    def send_header(self, h, value):
        self.responses['headers']['h']= value


    def end_headers(self):
        pass

    def send_request(self, r, path="method/", req_id=42):
        self.path = path
        jrequest = json.dumps(r)
        self.rfile.write(jrequest.encode('utf-8'))
        self.rfile.seek(0)
        self.headers["Content-Length"] = len(jrequest)
        self.headers["HTTP_X_REQUEST_ID"] = req_id


class TestResponseRequest:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.handler = MockedHttpHandler()


    @pytest.mark.parametrize(("request_body", "score_result"),
                             [({"account": "hornshoofs", "login": "hf","method": "online_score", "token": "",
                               "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru",
                                             "first_name": "stanislav", "last_name": "stupnikov",
                                             "birthday": "01.01.1990", "gender": 1}}, 5)],
                             ids=['valid_request-valid_path'])
    def test_http_handler_valid_request(self, request_body, score_result):
        request_body['token'] = gen_good_auth(request_body)
        self.handler.send_request(request_body)
        self.handler.do_POST()
        response = json.loads(self.handler.wfile.getvalue().decode())
        assert isinstance(response, dict)
        assert sorted(list(response.keys())) == ['code', 'response']
        assert response['code'] == 200
        assert response['response'] == {'score': score_result}


    @pytest.mark.parametrize(("request_body"),
                             [{"account": "hornshoofs", "login": "hf", "method": "online_score", "token": "",
                               "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru",
                                             "first_name": "stanislav", "last_name": "stupnikov",
                                             "birthday": "01.01.1990", "gender": 1}}],
                             ids=['valid_request-not_valid_path'])
    def test_http_handler_invalid_path(self, request_body):
        request_body['token'] = gen_good_auth(request_body)
        self.handler.send_request(request_body, path='/invalid')
        self.handler.do_POST()
        response = json.loads(self.handler.wfile.getvalue().decode())
        assert isinstance(response, dict)
        assert sorted(list(response.keys())) == ['code', 'error']
        assert response['code'] == 404
        assert response['error'] == 'Not Found'

    @pytest.mark.parametrize(("request_body"),
                             [{"account": "hornshoofs", "login": "hf", "method": "online_score", "token": "",
                               "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru",
                                             "first_name": "stanislav", "last_name": "stupnikov",
                                             "birthday": "01.01.1990", "gender": 1}}],
                             ids=['invalid_request-empty_token'])
    def test_http_handler_bad_auth(self, request_body):
        self.handler.send_request(request_body)
        self.handler.do_POST()
        response = json.loads(self.handler.wfile.getvalue().decode())
        assert isinstance(response, dict)
        assert sorted(list(response.keys())) == ['code', 'error']
        assert response['code'] == 403
        assert response['error'] == 'Forbidden'

    @pytest.mark.parametrize(("request_body"),
                             [{"account": "hornshoofs", "login": "hf", "method": "online_score", "token": "",
                               "arguments": {"pne": "79175002040", "email": "stupnikov@otus.ru",
                                             "first_name": "stanislav", "last_name": "stupnikov",
                                             "birthday": "01.01.1990", "gender": 1}}],
                             ids=['unexpected_argument_case_pne_instead_of_phone'])
    def test_http_handler_internal_server_error(self, request_body):
        request_body['token'] = gen_good_auth(request_body)
        self.handler.send_request(request_body)
        self.handler.do_POST()
        response = json.loads(self.handler.wfile.getvalue().decode())
        assert isinstance(response, dict)
        assert sorted(list(response.keys())) == ['code', 'error']
        assert response['code'] == 500
        assert response['error'] == 'Internal Server Error'

    @pytest.mark.parametrize(("request_body"),
                             [""],
                             ids=['empty_request_and_corrupted_headers_then'])
    def test_http_handler_bad_request(self, request_body):
        self.handler.send_request(request_body)
        self.handler.headers = {}
        self.handler.do_POST()
        response = json.loads(self.handler.wfile.getvalue().decode())
        assert isinstance(response, dict)
        assert sorted(list(response.keys())) == ['code', 'error']
        assert response['code'] == 400
        assert response['error'] == 'Bad Request'

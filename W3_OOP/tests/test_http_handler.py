import requests
import pytest
from .context import api
import hashlib
import datetime
import json

# BEFORE RUNNING THIS TEST YOU HAVE TO RUN HTTP-SERVER WITH THE FOLLOWING PARAMETERS:
# - ip-address http://127.0.0.1
# - port 8080

def gen_good_auth(request_body):
    if request_body['login'] == api.ADMIN_LOGIN:
        code_for_hash = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()
    else:
        code_for_hash = (request_body['account'] + request_body['login'] + api.SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()



@pytest.mark.parametrize(("request_body", "request_header"),
                         [('{"account": "hornshoofs", "login": "hf",\n"method": "online_score", "token": "", '
                          '"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": '
                          '"stanislav", "last_name": "stupnikov", "birthday": "01.01.1990", "gender": 1}}',
                          {'Content-Type': 'application/json',})], ids=['valid_request'])
def test_http_handler_valid_request(request_body, request_header):
    request_body = json.loads(request_body)
    request_body['token'] = gen_good_auth(request_body)
    request_body = json.dumps(request_body)
    response = requests.post('http://127.0.0.1:8080/method/', headers=request_header, data=request_body)
    assert response.status_code == 200

@pytest.mark.parametrize(("request_body", "request_header"),
                         [('{"account": "hornshoofs", "login": "hf",\n"method": "online_score", "token": "", '
                          '"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": '
                          '"stanislav", "last_name": "stupnikov", "birthday": "01.01.1990", "gender": 1}}',
                          {'Content-Type': 'application/json',})], ids=['valid_request-wrong-path'])
def test_http_handler_wrong_path(request_body, request_header):
    request_body = json.loads(request_body)
    request_body['token'] = gen_good_auth(request_body)
    request_body = json.dumps(request_body)
    response = requests.post('http://127.0.0.1:8080/met/', headers=request_header, data=request_body)
    assert response.status_code == 404


@pytest.mark.parametrize(("request_body", "request_header"),
                         [('{'"account"': "hornshoofs", "login": "hf",\n"method": "online_score", "token": "", '
                          '"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": '
                          '"stanislav", "last_name": "stupnikov", "birthday": "01.01.1990", "gender": 1}}',
                          {'Content-Type': 'application/json',})], ids=['account_field_with_excessive_quotes'])
def test_http_handler_bad_request(request_body, request_header):
    response = requests.post('http://127.0.0.1:8080/method/', headers=request_header, data=request_body)
    assert response.status_code == 400


@pytest.mark.parametrize(("request_body", "request_header"),
                         [('{"ount": "hornshoofs", "login": "hf",\n"method": "online_score", "token": "", '
                          '"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": '
                          '"stanislav", "last_name": "stupnikov", "birthday": "01.01.1990", "gender": 1}}',
                          {'Content-Type': 'application/json',})], ids=['ount instead of account'])
def test_http_handler_internal_error(request_body, request_header):
    response = requests.post('http://127.0.0.1:8080/method/', headers=request_header, data=request_body)
    assert response.status_code == 500

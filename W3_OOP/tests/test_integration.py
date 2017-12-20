import pytest
from .context import store
from .context import api
import datetime
import hashlib


def gen_good_auth(request_body):
    if request_body['login'] == api.ADMIN_LOGIN:
        code_for_hash = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()
    else:
        code_for_hash = (request_body['account'] + request_body['login'] + api.SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()


class TestResponseRequest:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.context = {}
        self.headers = {}
        self.store = store.Store()

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    @pytest.mark.parametrize("bad_auth_request", [
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments":{}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments":{}},
        ], ids=["no-token-user", "fake-token-user", "no-token-admin"])
    def test_bad_auth(self, bad_auth_request):
        param_input, expected_output = bad_auth_request, api.FORBIDDEN
        _, result_code = self.get_response(param_input)
        assert result_code == expected_output



    @pytest.mark.parametrize("bad_request", [
        # {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "offline_score", "token":"", "arguments": {}},
        ], ids=["empty_arguments", "invalid method"])
    def test_invalid_request(self, bad_request):
        param_input = bad_request
        param_input['token'] = gen_good_auth(param_input)
        error_msg, result_code = self.get_response(param_input)
        expected_output = api.INVALID_REQUEST
        print(error_msg)
        assert expected_output == result_code


class TestOnlineScoreMethod:
    @pytest.fixture(scope='function',autouse=True)
    def setup(self):
        self.context = {}
        self.headers = {}
        self.store = store.Store()

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    @pytest.mark.parametrize(("query", "expected_output"), [
        ({ "account": "hf", "login": "123", "method": "online_score", "token": "123", "arguments":
        {"phone": "71234567890", "email": "a@b.ru", "first_name": "Stan","last_name": "Stupnikov",
        "birthday": "01.01.1991", "gender": 1}}, 5),
        ({"account": "hf", "login": "123", "method": "online_score", "token": "123", "arguments":
            {"phone": "71234567890", "email": "a@b.ru", "first_name": "Ivan", "last_name": "",
             "birthday": "01.01.1991", "gender": 1}}, 4.5),
        ({"account": "hf", "login": "admin", "method": "online_score", "token": "123", "arguments":
            {"phone": "71234567890", "email": "a@b.ru", "first_name": "Ivan", "last_name": "",
             "birthday": "01.01.1991", "gender": 1}}, 43),
    ],
    ids=["user-all_fields", "user_no_last_name", "admin_no_last_name"])
    def test_correct_score_calculation(self, query, expected_output):
        '''
        here we could enhance tests by checking every component of score formula. But because it educational example,
        we don't do it
        '''
        param_input, expected_output = query, expected_output
        param_input['token'] = gen_good_auth(param_input)
        result, _= self.get_response(param_input)
        assert float(result['score']) == float(expected_output)

    @pytest.mark.parametrize(("query", "field_to_remove"), [
        ({"account": "hf", "login": "123", "method": "online_score", "token": "123", "arguments":
            {"phone": "71234567890", "email": "a@b.ru", "first_name": "Stan", "last_name": "Stupnikov",
             "birthday": "01.01.1991", "gender": 1}}, "email"),
        ], ids=["user-all_fields_remove_last_name"])
    def test_check_cache(self, query, field_to_remove):

        '''
        at the beginnig we calculate score and think that it should be in cache. Then remove the field that should
        reduce score but expect that score won't change because it will be retrieved from cache
        You should NOT change first name, last name or birthday (only email, phone and gender are available)
        '''

        params_initial, field_to_remove = query, field_to_remove
        params_initial['token'] = gen_good_auth(params_initial)
        result_initial, _ = self.get_response(params_initial)
        params_new = params_initial
        params_new[field_to_remove] = ""
        result_new, _ = self.get_response(params_new)
        assert float(result_initial['score']) == float(result_new['score'])

    @pytest.mark.parametrize("bad_request", [
        {"account": "hf", "login": "123", "method": "online_score", "token": "123", "arguments":
            {"phone": "71234567890", "email": "", "first_name": "Stan", "last_name": "",
             "birthday": "01.01.1991", "gender": ""}},
    ], ids=["missed_email_last_name_gender"])
    def test_missed_required_arguments(self, bad_request):

        '''
        at the beginnig we calculate score and think that it should be in cache. Then remove the field that should
        reduce score but expect that score won't change because it will be retrieved from cache
        You should NOT change first name, last name or birthday (only email, phone and gender are available)
        '''

        param_input = bad_request
        param_input['token'] = gen_good_auth(param_input)
        error_msg, result_code = self.get_response(param_input)
        expected_output = api.INVALID_REQUEST
        print(error_msg)
        assert expected_output == result_code


class TestGetInterestMethod:
    @pytest.fixture(scope='function', autouse=True)
    def setup(self):
        self.context = {}
        self.headers = {}
        self.store = store.Store()

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    @pytest.mark.parametrize(("query", "expected_output"), [
        ({"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token":"",
         "arguments": {"client_ids": [1, 2], "date": "20.07.2017"}},
         {'1': ['cars', 'pets', 'sport'], '2': ['hi-tech', 'music', 'tv']}),
        ({"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token": "",
          "arguments": {"client_ids": [1], "date": ""}}, {'1': ['cars', 'pets', 'sport']}),
        ({"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token": "",
          "arguments": {"client_ids": [6], "date": "20.07.2017"}}, {})
    ],
        ids=["existing_ids_with_date", "existing_ids_without_date", "no_existing_id_with_date"])
    def test_correct_score_calculation(self, query, expected_output):
        '''
        here we could enhance tests by checking every component of score formula. But because it educational example,
        we don't do it
        '''
        param_input, expected_output = query, expected_output
        param_input['token'] = gen_good_auth(param_input)
        result, _= self.get_response(param_input)
        assert result == expected_output

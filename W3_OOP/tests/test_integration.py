import pytest
from .context import store
from .context import api
from .context import scoring_new
import datetime
import hashlib


def gen_good_auth(request_body):
    if request_body['login'] == api.ADMIN_LOGIN:
        code_for_hash = (datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()
    else:
        code_for_hash = (request_body['account'] + request_body['login'] + api.SALT).encode('utf-8')
        return hashlib.sha512(code_for_hash).hexdigest()

bad_config_db = {'MAIN':{'host':"localhost",
                         'user': "root",
                         'password': "kromanov",
                         'db_store': "",
                         'db_cache':"otus_db",
                         'query_timeout': 5,
                         'db_connect_timeout': 5,
                         'reconnect': 10
                         }}


class TestResponseRequest:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.context = {}
        self.headers = {}
        self.store = store.Store(api.db_config)

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



    @pytest.mark.parametrize("invalid_request", [
        # {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "offline_score", "token":"", "arguments": {}},
        ], ids=["empty_arguments", "invalid method"])
    def test_invalid_request(self, invalid_request):
        param_input = invalid_request
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
        self.good_store = store.Store(api.db_config)
        self.bad_store = store.Store(bad_config_db)
        # self.get_score =

    def get_response_good_store(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.good_store)

    def get_response_bad_store(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.bad_store)

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
        result, _ = self.get_response_good_store(param_input)
        assert float(result['score']) == float(expected_output)

    @pytest.mark.parametrize(("query", "field_to_remove"), [
        ({"account": "hf", "login": "123", "method": "online_score", "token": "123", "arguments":
            {"phone": "71234567890", "email": "a@b.ru", "first_name": "Stan", "last_name": "Stupnikov",
             "birthday": "01.01.1991", "gender": 1}}, "email"),
        ], ids=["user-all_fields_remove_last_name"])
    def test_check_cache_when_change_parameters(self, query, field_to_remove):

        '''
        at the beginnig we calculate score and think that it should be in cache. Then remove the field that should
        reduce score but expect that score won't change because it will be retrieved from cache
        You should NOT change first name, last name or birthday (only email, phone and gender are available)
        '''

        params_initial, field_to_remove = query, field_to_remove
        params_initial['token'] = gen_good_auth(params_initial)
        result_initial, _ = self.get_response_good_store(params_initial)
        params_new = params_initial
        params_new[field_to_remove] = ""
        result_new, _ = self.get_response_good_store(params_new)
        assert float(result_initial['score']) == float(result_new['score'])

    @pytest.mark.parametrize("query", [
        {"account": "hf", "login": "123", "method": "online_score", "token": "123", "arguments":
            {"phone": "71234567890", "email": "a@b.ru", "first_name": "Stan", "last_name": "Stupnikov",
             "birthday": "01.01.1991", "gender": 1}}], ids=["user-all_fields_disable_store"])
    def test_check_cache_when_shutdown_store(self, query):

        '''
        at the beginnig we calculate score and think that it should be in cache. Then change db_config where db_store
        is empty and rerun calculation. Now, though we don't have an access to store db, we have to get result from
        cache)
        '''

        params_initial = query
        params_initial['token'] = gen_good_auth(params_initial)
        result_initial, _ = self.get_response_good_store(params_initial)
        self.good_store.conn['store'] = None
        self.good_store.conn['cache'] = None
        print(params_initial['arguments'].keys())
        result_new = scoring_new.get_score(store=self.good_store,
                                           phone=params_initial['arguments'].get('phone', None),
                                           email=params_initial['arguments'].get('email',None),
                                           birthday=params_initial['arguments'].get('birthday', None),
                                           gender=params_initial['arguments'].get('gender', None),
                                           first_name=params_initial['arguments'].get('first_name', None),
                                           last_name=params_initial['arguments'].get('last_name', None))

        assert float(result_initial['score']) == float(result_new)

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
        error_msg, result_code = self.get_response_good_store(param_input)
        expected_output = api.INVALID_REQUEST
        print(error_msg)
        assert expected_output == result_code


class TestGetInterestMethod:
    @pytest.fixture(scope='function', autouse=True)
    def setup(self):
        self.context = {}
        self.headers = {}
        self.good_store = store.Store(api.db_config)
        self.bad_store = store.Store(bad_config_db)

    def get_response_good_store(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.good_store)

    def get_response_bad_store(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.bad_store)

    @pytest.mark.parametrize(("query", "expected_output"), [
        ({"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token": "",
         "arguments": {"client_ids": [1, 2], "date": "20.07.2017"}},
         [{'client_id': 1, 'interests': 'cars pets sport'}, {'client_id': 2, 'interests': 'hi-tech music tv'}]),
        ({"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token": "",
          "arguments": {"client_ids": [1], "date": ""}}, [{'client_id': 1, 'interests': 'cars pets sport'}]),
        ({"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token": "",
          "arguments": {"client_ids": [6], "date": "20.07.2017"}}, [])
    ],
        ids=["existing_ids_with_date", "existing_ids_without_date", "no_existing_id_with_date"])
    def test_correct_query(self, query, expected_output):
        '''
        here we could enhance tests by checking every component of score formula. But because it educational example,
        we don't do it
        '''
        param_input, expected_output = query, expected_output
        param_input['token'] = gen_good_auth(param_input)
        result, _ = self.get_response_good_store(param_input)
        assert result == expected_output

    def test_try_get_interests_from_bad_store(self):
        param_input = {"account": "horns&hoofs", "login": "ff", "method": "clients_interests", "token": "",
         "arguments": {"client_ids": [1, 2], "date": "20.07.2017"}}
        param_input['token'] = gen_good_auth(param_input)
        with pytest.raises(Exception):
            result, _ = self.get_response_bad_store(param_input)


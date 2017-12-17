import unittest

import api


class TestSuite(unittest.TestCase):
    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = None

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    # def test_empty_request(self):
    #     _, code = self.get_response({})
    #     self.assertEqual(api.INVALID_REQUEST, code)

    def test_request_interest(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests",
                   "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                   "arguments": {"date": "15.12.2017", "client_ids": [1, 2, 3]}}
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)

    def test_request_interest2(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests",
                   "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                   "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Станиcлав",
                                 "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)

    def test_request_interest3(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests",
                   "token": "5cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                   "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Станиcлав",
                                 "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}
        response, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    def test_request_interest4(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests",
                    "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                    "arguments": {"date": "15.12.2017"}}
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)

    def test_request_score(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score",
                   "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                   "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Станиcлав",
                                 "last_name": "Ступников", "birthday": "01.01.1990", "gender": 1}}
        # -> {"code": 200, "response": {"score": 5.0}}
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(5.0, response["score"])

    def test_request_score2(self):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score",
                   "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                   "arguments": {}}
        # -> {"code": 200, "response": {"score": 0}}
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(0, response["score"])

    def test_request_score_admin(self):
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score",
                   "token": "d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f24091386050205c324687a0",
                   "arguments": {}}
        response, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)
        # self.assertEqual(42, response["score"])

if __name__ == "__main__":
    unittest.main()

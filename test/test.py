#!/usr/bin/env python3 -X utf8
import json
import os
import tempfile
from time import sleep
import pytest
import requests
from mock import Mock

from fuzzer import Fuzzer
from test.test_utils import get_test_server_pid


@pytest.fixture(scope="class")
def resource():
    print("setup")
    sleep(2)
    if get_test_server_pid() is not None:
        os.system("python3 ./test_application.py &")
    yield "resource"
    print("teardown")
    sleep(2)
    pid = get_test_server_pid()
    if pid is not None:
        os.kill(pid, 9)


class TestClass(object):

    @classmethod
    def setup_class(cls):
        print('\nsetup_class()')
        cls.report_dir = tempfile.mkdtemp()
        cls.test_app_url = "http://127.0.0.1:5000/"
        if not get_test_server_pid():
            print('Start test app')
            os.system("python3 ./test_application.py &")
        with open('./test_swagger_definition.json', 'r') as f:
            cls.swagger = json.loads(f.read())

    @classmethod
    def teardown_class(cls):
        print ('teardown_class()')
        pid = get_test_server_pid()
        if pid:
            os.kill(pid, 9)

    def query_last_call(self):
        _resp = requests.get('{}/{}'.format(self.test_app_url, 'last_call'))
        assert _resp.status_code == 200, "status code mismatch expected {} received {}".format(200, _resp.status_code)
        return json.loads(_resp.text)

    def fuzz(self, api_resources):
        """
        Call APIFuzzer with the given api definition
        :type api_resources: dict
        """
        with pytest.raises(SystemExit):
            prog = Fuzzer(api_resources=api_resources,
                          report_dir=self.report_dir,
                          test_level=1,
                          alternate_url=self.test_app_url,
                          test_result_dst=None,
                          log_level='Debug',
                          auth_headers={}
                          )
            prog.prepare()
            prog.run()

    def test_something(self):
        sleep(1)
        pass

    def test_integer_status_code(self):
        api_endpoint_to_test = self.swagger['paths']['/exception/{integer_id}']
        print('API to test: {}'.format(api_endpoint_to_test))
        self.swagger.pop('paths')
        self.swagger['paths'] = {}
        self.swagger['paths']['/exception/{integer_id}']= api_endpoint_to_test
        self.fuzz(self.swagger)
        last_call = self.query_last_call()
        #last_call:
        # "path": "/exception/\u001f/\u001c\u007f\u0000N@",
        assert last_call['status_code'] == 500, last_call['status_code'] + "Received"

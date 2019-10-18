from __future__ import print_function

import json

from test.utils import get_test_server_pid
from test.test_application import app


class BaseTestClass(object):

    @classmethod
    def setup_class(cls):
        if not get_test_server_pid():
            app.run(debug=True)
        with open('./test_swagger_definition.json', 'r') as f:
            cls.swagger = json.loads(f.read())

    @classmethod
    def teardown_class(cls):
        pass

    def test_1_that_needs_resource_a(self):
        self.swagger.pop()

from __future__ import print_function
import pytest
import psutil
from test_application import app
from utils import get_test_server_pid
from fuzzer import Fuzzer


class BaseTestClass(object):

    @classmethod
    def setup_class(cls):
        if not get_test_server_pid():
            app.run(debug=True)

    @classmethod
    def teardown_class(cls):


    def test_1_that_needs_resource_a(self):
        print('\ntest_1_that_needs_resource_a()')

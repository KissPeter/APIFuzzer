import json
import os
import urllib.parse
from io import BytesIO
from time import time

import pycurl
from bitstring import Bits
from junit_xml import TestSuite, TestCase, to_xml_report_file
from kitty.targets.server import ServerTarget

from apifuzzer.apifuzzer_report import Apifuzzer_Report as Report
from apifuzzer.fuzzer_target.request_base_functions import FuzzerTargetBase
from apifuzzer.utils import try_b64encode, init_pycurl, get_logger


class Return:
    pass


class FuzzerTarget(FuzzerTargetBase, ServerTarget):

    def not_implemented(self, func_name):
        pass

    def __init__(self, name, base_url, report_dir, auth_headers, junit_report_path):
        super(ServerTarget, self).__init__(name)
        super(FuzzerTargetBase, self).__init__(auth_headers)
        self.logger = get_logger(self.__class__.__name__)
        self.base_url = base_url
        self.accepted_status_codes = list(range(200, 300)) + list(range(400, 500))
        self.auth_headers = auth_headers
        self.report_dir = report_dir
        self.junit_report_path = junit_report_path
        self.failed_test = list()
        self.logger.info('Logger initialized')
        self.resp_headers = dict()

    def pre_test(self, test_num):
        """
        Called when a test is started
        """
        self.test_number = test_num
        self.report = Report(self.name)
        if self.controller:
            self.controller.pre_test(test_number=self.test_number)
        for monitor in self.monitors:
            monitor.pre_test(test_number=self.test_number)
        self.report.add('test_number', test_num)
        self.report.add('state', 'STARTED')

    def transmit(self, **kwargs):
        """
        Prepares fuzz HTTP request, sends and processes the response
        :param kwargs: url, method, params, querystring, etc
        :return:
        """
        self.logger.debug('Transmit: {}'.format(kwargs))
        try:
            _req_url = list()
            for url_part in self.base_url, kwargs['url']:
                if isinstance(url_part, Bits):
                    url_part = url_part.tobytes()
                if isinstance(url_part, bytes):
                    url_part = url_part.decode()
                _req_url.append(url_part.strip('/'))
            kwargs.pop('url')
            # Replace back the placeholder for '/'
            # (this happens in expand_path_variables,
            # but if we don't have any path_variables, it won't)
            request_url = '/'.join(_req_url).replace('+', '/')
            query_params = None

            if kwargs.get('params') is not None:
                self.logger.debug(('Adding query params: {}'.format(kwargs.get('params', {}))))
                query_params = self.format_pycurl_query_param(request_url, kwargs.get('params', {}))
                kwargs.pop('params')
            if kwargs.get('path_variables') is not None:
                request_url = self.expand_path_variables(request_url, kwargs.get('path_variables'))
                kwargs.pop('path_variables')
            if kwargs.get('data') is not None:
                kwargs['data'] = self.fix_data(kwargs.get('data'))
            if query_params is not None:
                request_url = '{}{}'.format(request_url, query_params)
            method = kwargs['method']
            content_type = kwargs.get('content_type')
            kwargs.pop('content_type', None)
            self.logger.info('Request URL : {} {}'.format(method, request_url))
            if kwargs.get('data') is not None:
                self.logger.info('Request data:{}'.format(json.dumps(dict(kwargs.get('data')))))
            if isinstance(method, Bits):
                method = method.tobytes()
            if isinstance(method, bytes):
                method = method.decode()
            kwargs.pop('method')
            kwargs['headers'] = self.compile_headers(kwargs.get('headers'))
            self.logger.debug('Request url:{}\nRequest method: {}\nRequest headers: {}\nRequest body: {}'.format(
                request_url, method, json.dumps(dict(kwargs.get('headers', {})), indent=2), kwargs.get('data')))
            self.report.set_status(Report.PASSED)
            self.report.add('request_url', request_url)
            self.report.add('request_method', method)
            self.report.add('request_headers', json.dumps(dict(kwargs.get('headers', {}))))
            try:
                resp_buff_hdrs = BytesIO()
                resp_buff_body = BytesIO()
                buffer = BytesIO()
                _curl = init_pycurl()
                _curl.setopt(pycurl.URL, self.format_pycurl_url(request_url))
                _curl.setopt(pycurl.HEADERFUNCTION, self.header_function)
                _curl.setopt(pycurl.POST, len(kwargs.get('data', {}).items()))
                _curl.setopt(pycurl.CUSTOMREQUEST, method)
                headers = kwargs['headers']
                if content_type:
                    self.logger.debug(f'Adding Content-Type: {content_type} header')
                    headers.update({"Content-Type": content_type})
                _curl.setopt(pycurl.HTTPHEADER, self.format_pycurl_header(headers))
                if content_type == 'multipart/form-data':
                    post_data = list()
                    for k, v in kwargs.get('data', {}).items():
                        post_data.append((k, v))
                    _curl.setopt(pycurl.HTTPPOST, post_data)
                elif content_type == 'application/json':
                    _curl.setopt(pycurl.POSTFIELDS, json.dumps(kwargs.get('data', {}), indent=2, ensure_ascii=False))
                else:
                    # default content type: application/x-www-form-urlencoded
                    _curl.setopt(pycurl.POSTFIELDS, urllib.parse.urlencode(kwargs.get('data', {})))
                _curl.setopt(pycurl.HEADERFUNCTION, resp_buff_hdrs.write)
                _curl.setopt(pycurl.WRITEFUNCTION, resp_buff_body.write)
                for retries in reversed(range(0, 3)):
                    try:
                        _curl.perform()
                        # TODO: Handle this: pycurl.error: (3, 'Illegal characters found in URL')
                    except pycurl.error as e:
                        self.logger.warning(f'Failed to send request because of {e}')
                    except Exception as e:
                        if retries:
                            self.logger.error('Retrying... ({}) because {}'.format(retries, e))
                        else:
                            raise e
                _return = Return()
                _return.status_code = _curl.getinfo(pycurl.RESPONSE_CODE)
                _return.headers = self.resp_headers
                _return.content = buffer.getvalue()
                _return.request = Return()
                _return.request.headers = kwargs.get('headers', {})
                _return.request.body = kwargs.get('data', {})
                _curl.close()
            except Exception as e:
                self.logger.exception(e)
                self.report.set_status(Report.FAILED)
                self.logger.error('Request failed, reason: {}'.format(e))
                # self.report.add('request_sending_failed', e.msg if hasattr(e, 'msg') else e)
                self.report.add('request_method', method)
                return
            # overwrite request headers in report, add auto generated ones
            self.report.add('request_headers', try_b64encode(json.dumps(dict(_return.request.headers))))
            self.logger.debug('Response code:{}\nResponse headers: {}\nResponse body: {}'.format(
                _return.status_code, json.dumps(dict(_return.headers), indent=2), _return.content))
            self.report.add('request_body', _return.request.body)
            self.report.add('response', _return.content.decode())
            status_code = _return.status_code
            if not status_code:
                self.logger.warning(f'Failed to parse http response code, continue...')
                self.report.set_status(Report.PASSED)
            elif status_code not in self.accepted_status_codes:
                self.report.add('parsed_status_code', status_code)
                self.report_add_basic_msg(('Return code %s is not in the expected list:', status_code))
            return _return
        except (UnicodeDecodeError, UnicodeEncodeError) as e:  # request failure such as InvalidHeader
            self.report_add_basic_msg(('Failed to parse http response code, exception occurred: %s', e))

    def post_test(self, test_num):
        """Called after a test is completed, perform cleanup etc."""
        if self.report.get('report') is None:
            self.report.add('reason', self.report.get_status())
        super(ServerTarget, self).post_test(test_num)
        if self.report.get_status() != Report.PASSED:
            if self.junit_report_path:
                test_case = TestCase(name=self.test_number, status=self.report.get_status())
                test_case.add_failure_info(message=json.dumps(self.report.to_dict()))
                self.failed_test.append(test_case)
            self.save_report_to_disc()

    def save_report_to_disc(self):
        self.logger.info('Report: {}'.format(self.report.to_dict()))
        try:
            if not os.path.exists(os.path.dirname(self.report_dir)):
                try:
                    os.makedirs(os.path.dirname(self.report_dir))
                except OSError:
                    pass
            with open('{}/{}_{}.json'.format(self.report_dir, self.test_number, time()), 'w') as report_dump_file:
                report_dump_file.write(json.dumps(self.report.to_dict()))
        except Exception as e:
            self.logger.error('Failed to save report "{}" to {} because: {}'
                              .format(self.report.to_dict(), self.report_dir, e))

    def report_add_basic_msg(self, msg):
        self.report.set_status(Report.FAILED)
        self.logger.warning(msg)
        self.report.failed(msg)

    def teardown(self):
        if len(self.failed_test):
            test_cases = self.failed_test
        else:
            test_cases = list()
            test_cases.append(TestCase(name='Fuzz test succeed', status='Pass'))
        if self.junit_report_path:
            with open(self.junit_report_path, 'w') as report_file:
                to_xml_report_file(report_file, [TestSuite("API Fuzzer", test_cases)], prettyprint=True)
        super(ServerTarget, self).teardown()

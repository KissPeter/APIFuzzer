import json
import os
import re
from time import time

import requests
from bitstring import Bits
from kitty.targets.server import ServerTarget
from requests.exceptions import RequestException

from apifuzzer.apifuzzer_report import Apifuzzer_report as Report
from apifuzzer.utils import set_class_logger, try_b64encode


@set_class_logger
class FuzzerTarget(ServerTarget):
    def not_implemented(self, func_name):
        pass

    def __init__(self, name, base_url, report_dir, auth_headers, logger):
        super(FuzzerTarget, self).__init__(name, logger)
        self.base_url = base_url
        self._last_sent_request = None
        self.accepted_status_codes = list(range(200, 300)) + list(range(400, 500))
        self.auth_headers = auth_headers
        self.report_dir = report_dir
        self.logger = logger
        self.logger.info('Logger initialized')

    def pre_test(self, test_num):
        '''
        Called when a test is started
        '''
        self.test_number = test_num
        self.report = Report(self.name)
        if self.controller:
            self.controller.pre_test(test_number=self.test_number)
        for monitor in self.monitors:
            monitor.pre_test(test_number=self.test_number)
        self.report.add('test_number', test_num)
        self.report.add('state', 'STARTED')

    def compile_headers(self, fuzz_header=None):
        """
        Using the fuzzer headers plus the header(s) defined at cli parameter this puts together a dict which will be
        used at the reques
        :type fuzz_header: list, dict, None
        """
        _header = dict()
        if isinstance(fuzz_header, dict):
            _header = fuzz_header
        if isinstance(self.auth_headers, list):
            for auth_header_part in self.auth_headers:
                _header.update(auth_header_part)
        else:
            _header.update(self.auth_headers)
        return _header

    def transmit(self, **kwargs):
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
            request_url = '/'.join(_req_url)
            for param in ['path_variables', 'params']:
                if kwargs.get(param) is not None:
                    request_url = self.expand_path_variables(request_url, kwargs.get(param))
                    kwargs.pop(param)
            self.logger.info('Request URL : {}'.format(request_url))
            method = kwargs['method']
            if isinstance(method, Bits):
                method = method.tobytes()
            if isinstance(method, bytes):
                method = method.decode()
            kwargs.pop('method')
            kwargs['headers'] = self.compile_headers(kwargs.get('headers'))
            self.logger.debug('Request url:{}\nRequest method: {}\nRequest headers: {}\nRequest body: {}'.format(
                request_url, method, json.dumps(dict(kwargs.get('headers',{})), indent=2), kwargs.get('params')))
            self.report.set_status(Report.PASSED)
            self.report.add('request_url', try_b64encode(request_url))
            self.report.add('request_method', try_b64encode(method))
            self.report.add('request_headers', try_b64encode(kwargs.get('headers')))
            try:
                _return = requests.request(method=method, url=request_url, verify=False, timeout=10, **kwargs)
            except Exception as e:
                self.report.set_status(Report.FAILED)
                self.logger.error('Request failed, reason: {}'.format(e))
                self.report.add('request_sending_failed', e.reason if hasattr(e, 'reason') else e)
                self.report.add('request_method', try_b64encode(method))
                return
            # overwrite request headers in report, add auto generated ones
            self.report.add('request_headers', try_b64encode(_return.request.headers))
            self.logger.debug('Response code:{}\nResponse headers: {}\nResponse body: {}'.format(
                _return.status_code, json.dumps(dict(_return.headers), indent=2), _return.content))
            self.report.add('request_body', try_b64encode(_return.request.body))
            self.report.add('response', try_b64encode(_return.content))
            status_code = _return.status_code
            if not status_code:
                self.report.set_status(Report.FAILED)
                self.logger.warn('Failed to parse http response code')
                self.report.failed('Failed to parse http response code')
            elif status_code not in self.accepted_status_codes:
                self.report.add('Parsed status_code', status_code)
                self.report.set_status(Report.FAILED)
                self.logger.warn('Return code %s is not in the expected list', status_code)
                self.report.failed(('Return code %s is not in the expected list', status_code))
            return _return
        except (RequestException, UnicodeDecodeError, UnicodeEncodeError) as e:  # request failure such as InvalidHeader
            self.report.set_status(Report.FAILED)
            self.logger.warn('Failed to parse http response code, exception occurred')
            self.report.failed('Failed to parse http response code, exception occurred')

    def post_test(self, test_num):
        """Called after a test is completed, perform cleanup etc."""
        if self.report.get('report') is None:
            self.report.add('reason', self.report.get_status())
        super(FuzzerTarget, self).post_test(test_num)
        if self.report.get_status() != Report.PASSED:
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
            self.logger.error('Failed to save report "{}" to {} because: {}'.format(self.report, self.report_dir, e))
            pass

    def expand_path_variables(self, url, path_parameters):
        if not isinstance(path_parameters, dict):
            self.logger.warn('Path_parameters {} does not in the desired format,received: {}'.format(path_parameters, type(path_parameters)))
            return url
        for path_key, path_value in path_parameters.items():
            self.logger.debug('Processing: path_key: {} , path_variable: {}'.format(path_key, path_value))
            try:
                _temporally_url_list = list()
                path_parameter = path_key.split('|')[-1]
                splitter = '({' + path_parameter + '})'
                url_list = re.split(splitter, url)
                for url_part in url_list:
                    if url_part == '{' + path_parameter + '}':
                        _temporally_url_list.append(path_value)
                        # _temporally_url_list.append(path_value.decode('unicode-escape').encode('utf8'))
                    else:
                        _temporally_url_list.append(url_part)
                        # _temporally_url_list.append(url_part.encode())
                url = "".join(_temporally_url_list)
                # self.logger.info('Compiled url In {} + {}, out: {}'.format(url, path_parameter, path_value))
            except Exception as e:
                self.logger.warn(
                    'Failed to replace string in url: {} param: {}, exception: {}'.format(url, path_value, e))
        url = url.replace("{", "").replace("}", "").replace("+", "/")
        return url

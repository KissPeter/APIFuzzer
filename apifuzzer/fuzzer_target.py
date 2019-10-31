#  -*- coding: utf-8 -*-
# encoding: utf-8

import json
import os
import re
from base64 import b64encode
from time import time

import requests
from bitstring import Bits
from kitty.data.report import Report
from kitty.targets.server import ServerTarget
from requests.exceptions import RequestException

from apifuzzer.utils import set_class_logger


@set_class_logger
class FuzzerTarget(ServerTarget):
    def not_implemented(self, func_name):
        pass

    def __init__(self, name, base_url, report_dir, logger):
        super(FuzzerTarget, self).__init__(name, logger)
        self.base_url = base_url
        self._last_sent_request = None
        self.accepted_status_codes = list(range(200, 300)) + list(range(400, 500))
        self.report_dir = report_dir
        self.logger = logger
        self.logger.info('Logger initialized')

    @staticmethod
    def try_b64encode(data_in):
        try:
            return b64encode(data_in)
        except TypeError:
            return data_in

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
            if kwargs.get('path_variables') is not None:
                request_url = self.expand_path_variables(request_url, kwargs.get('path_variables'))
                kwargs.pop('path_variables')
            if kwargs.get('params') is not None:
                request_url = self.expand_path_variables(request_url, kwargs.get('params'))
                kwargs.pop('params')
            self.logger.info('Request URL : {}'.format(request_url ))
            # if kwargs.get('path_variables'):
            #     kwargs.pop('path_variables')
            method = kwargs['method']
            if isinstance(method, Bits):
                method = method.tobytes()
            if isinstance(method, bytes):
                method = method.decode()
            kwargs.pop('method')
            self.logger.debug('Request kwargs:{}, url: {}, method: {}'.format(kwargs, request_url, method))
            _return = requests.request(method=method, url=request_url, **kwargs)
            self.report.set_status(Report.PASSED)
            self.report.add('request_url', _return.request.url)
            self.report.add('request_method', _return.request.method)
            self.report.add('request_body', _return.request.body)
            self.report.add('response', _return.text)
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
            self.report.add('reason', self.report.get_name())
        super(FuzzerTarget, self).post_test(test_num)
        if self.report.get_status() != Report.PASSED:
            self.save_report_to_disc()

    def save_report_to_disc(self):
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
                self.logger.warn('Failed to replace string in url: {} param: {}, exception: {}'.format(url, path_value, e))
        url = url.replace("{", "").replace("}", "").replace("+","/")
        return url


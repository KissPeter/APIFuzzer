#  -*- coding: utf-8 -*-
# encoding: utf-8

import json
import os
from time import time
import re
import requests
from base64 import b64encode
from  bitstring import Bits
from kitty.data.report import Report
from kitty.targets.server import ServerTarget
from requests.exceptions import RequestException

from apifuzzer.utils import set_class_logger,transform_data_to_bytes


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

    def try_b64encode(self, data_in):
        try:
            return b64encode(data_in)
        except TypeError:
            return data_in

    def error_report(self, msg, req):
        if hasattr(req, 'request'):
            self.report.add('request method', req.request.method)
            self.report.add('request body', req.request.body)
            self.report.add('response', req.text)
        else:
            for k, v in req.items():
                if isinstance(v, dict):
                    for subkey, subvalue in v.items():
                        try:
                            self.report.add(subkey, self.try_b64encode(subvalue))
                        except TypeError:
                            self.logger.error('Failed to add field ({}) or value ({}) to report because '
                                              'unsupported type ({}), report the issue'.format(subkey, subvalue,
                                                                                               type(subvalue)))
                else:
                    self.report.add(k, self.try_b64encode(subvalue))
        self.report.set_status(Report.ERROR)
        self.report.error(msg)

    def save_report_to_disc(self):
        try:
            if not os.path.exists(os.path.dirname(self.report_dir)):
                try:
                    os.makedirs(os.path.dirname(self.report_dir))
                except OSError:
                    pass
            with open('{}/{}_{}.json'.format(self.report_dir, self.test_number, time()), 'wb') as report_dump_file:
                report_dump_file.write(json.dumps(self.report.to_dict()))
        except Exception as e:
            self.logger.error('Failed to save report "{}" to {} because: {}'
                              .format(self.report, self.report_dir, e))

    def transmit(self, **kwargs):
        self.logger.debug('Transmit: {}'.format(kwargs))
        try:
            _req_url = list()
            for url_part in self.base_url, kwargs['url']:
                self.logger.info('URL part: {}, type {}'.format(url_part, type(url_part)))
                if isinstance(url_part, Bits):
                    url_part = url_part.tobytes()
                if isinstance(url_part, bytes):
                    url_part = url_part.decode()
                # url_part= transform_data_to_bytes(url_part).decode()
                self.logger.info('URL part 2: {}, type {}'.format(url_part, type(url_part)))
                # _req_url.append(url_part.strip('/'))
                _req_url.append(url_part)
            self.logger.warn('Request KWARGS:{}, url: {}'.format(kwargs, _req_url))
            request_url = '/'.join(_req_url)
            if kwargs.get('path_variables') is not None:
                request_url = self.expand_path_variables(request_url, kwargs.get('path_variables'))
            if kwargs.get('params') is not None:
                request_url = self.expand_path_variables(request_url, kwargs.get('params'))
            self.logger.info('Request URL : {}'.format(request_url ))
            if kwargs.get('path_variables'):
                kwargs.pop('path_variables')
            kwargs.pop('url')
            method = kwargs['method']
            if isinstance(method , Bits):
                method = method .tobytes()
            if isinstance(method , bytes):
                method = method .decode()
            kwargs.pop('method')
            _return = requests.request(method=method, url=request_url, **kwargs)
            status_code = _return.status_code
            if status_code:
                if status_code not in self.accepted_status_codes:
                    self.report.add('parsed status_code', status_code)
                    self.report.add('request method', _return.request.method)
                    self.report.add('request body', _return.request.body)
                    self.report.add('response', _return.text)
                    self.report.set_status(Report.FAILED)
                    self.report.failed('return code {} is not in the expected list'.format(status_code))
            else:
                self.error_report('Failed to parse http response code', _return.headers)
            return _return
        except (RequestException, UnicodeDecodeError, UnicodeEncodeError) as e:  # request failure such as InvalidHeader
            self.error_report('Failed to parse http response code, exception: {}'.format(e), kwargs)

    def post_test(self, test_num):
        """Called after a test is completed, perform cleanup etc."""
        super(FuzzerTarget, self).post_test(test_num)
        if self.report.get('status') != Report.PASSED:
            self.save_report_to_disc()

    def expand_path_variables(self, url, path_parameters):
        if not isinstance(path_parameters, dict):
            self.logger.error('Path_parameters {} does not in the desired format,received: {}'.format(path_parameters, type(path_parameters)))
            return url
        for path_key, path_value in path_parameters.items():
            self.logger.info('Processing: path_key: {} , path_variable: {}'.format(path_key, path_value))
            try:
                _temporally_url_list = list()
                path_parameter = path_key.split('|')[-1]
                splitter = '({' + path_parameter + '})'
                url_list = re.split(splitter, url)
                self.logger.info('Processing: {} key: {} splitter: {} '.format(url_list, path_parameter, splitter))
                for url_part in url_list:
                    if url_part == '{' + path_parameter + '}':
                        _temporally_url_list.append(path_value)
                        # _temporally_url_list.append(path_value.decode('unicode-escape').encode('utf8'))
                    else:
                        _temporally_url_list.append(url_part)
                        # _temporally_url_list.append(url_part.encode())
                url = "".join(_temporally_url_list)
                self.logger.info('url 1: {} | {}->{}'.format(url, path_parameter, path_value))
            except Exception as e:
                self.logger.warn('Failed to replace string in url: {} param: {}, exception: {}'.format(url, path_value, e))
        url = url.replace("{", "").replace("}", "")
        return url


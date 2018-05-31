#  -*- coding: utf-8 -*-
import json
from time import time
import re
import requests
from base64 import b64encode

from kitty.data.report import Report
from kitty.targets.server import ServerTarget
from requests.exceptions import RequestException

from utils import set_class_logger


@set_class_logger
class FuzzerTarget(ServerTarget):
    def not_implemented(self, func_name):
        pass

    def __init__(self, name, base_url, report_dir):
        super(FuzzerTarget, self).__init__(name)
        self.base_url = base_url
        self._last_sent_request = None
        self.accepted_status_codes = list(range(200, 300)) + list(range(400, 500))
        self.report_dir = report_dir
        self.logger.info('Logger initialized')

    def error_report(self, msg, req):
        if hasattr(req, 'request'):
            self.report.add('request method', req.request.method)
            self.report.add('request body', req.request.body)
            self.report.add('response', req.text)
        else:
            for k, v in req.items():
                if isinstance(v, dict):
                    for subkey, subvalue in v.items():
                        self.report.add(subkey, b64encode(subvalue))
                else:
                    self.report.add(k, b64encode(v))
        self.report.set_status(Report.ERROR)
        self.report.error(msg)

    def save_report_to_disc(self):
        try:
            with open('{}/{}_{}.json'.format(self.report_dir, self.test_number, time()), 'wb') as report_dump_file:
                report_dump_file.write(json.dumps(self.report.to_dict(), ensure_ascii=False, encoding='utf-8').encode('utf8'))
        except Exception as e:
            self.logger.error(
                'Failed to save report "{}" to {} because: {}'
                 .format(self.report.to_dict(), self.report_dir, e)
            )

    def transmit(self, **kwargs):
        try:
            _req_url = list()
            for url_part in self.base_url, kwargs['url']:
                self.logger.info('URL part: {}'.format(url_part))
                _req_url.append(url_part.strip('/'))
            self.logger.warn('Request KWARGS:{}, url: {}'.format(kwargs, _req_url))
            request_url = '/'.join(_req_url)
            request_url = self.expand_path_variables(request_url, kwargs.get('path_variables'))
            if kwargs.get('path_variables'):
                kwargs.pop('path_variables')
            kwargs.pop('url')
            self.logger.warn('>>> Formatted URL: {} <<<'.format(request_url))
            _return = requests.request(url=request_url, **kwargs)
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
                self.error_report('Failed to parse http response code', _return)
            return _return
        except (RequestException, UnicodeDecodeError) as e:  # request failure such as InvalidHeader
            self.error_report('Failed to parse http response code, exception: {}'.format(e), kwargs)
            pass

    def post_test(self, test_num):
        """Called after a test is completed, perform cleanup etc."""
        super(FuzzerTarget, self).post_test(test_num)
        if self.report.get('status') != Report.PASSED:
            self.save_report_to_disc()

    def expand_path_variables(self, url, path_parameters):
        for path_key, path_value in path_parameters.items():
            _temporally_url_list = list()
            splitter = '({' + path_key + '})'
            url_list = re.split(splitter, url)
            self.logger.info('Processing: {} key: {} splitter: {} '.format(url_list, path_key, splitter))
            for url_part in url_list:
                if url_part == '{' + path_key + '}':
                    _temporally_url_list.append(path_value.encode())
                else:
                    _temporally_url_list.append(url_part)
            try:
                url = "".join(_temporally_url_list)
            except Exception as e:
                self.logger.error(e)
            self.logger.warn('url 1: {} | {}->{}'.format(url, path_key, path_value))
        url = url.replace("{", "").replace("}", "")
        return url


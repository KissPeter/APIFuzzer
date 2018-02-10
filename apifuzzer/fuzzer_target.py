import json
from time import time

import requests
from kitty.data.report import Report
from kitty.targets.server import ServerTarget
from requests.exceptions import RequestException


class FuzzerTarget(ServerTarget):
    def not_implemented(self, func_name):
        pass

    def __init__(self, name, base_url, report_dir, logger=None):
        super(FuzzerTarget, self).__init__(name, logger)
        self.base_url = base_url
        self.logger = logger
        self._last_sent_request = None
        self.accepted_status_codes = list(range(200, 300)) + list(range(400, 500))
        self.report_dir = report_dir

    def error_report(self, msg, req):
        if hasattr(req, 'request'):
            self.report.add('request method', req.request.method)
            self.report.add('request body', req.request.body)
            self.report.add('response', req.text)
        else:
            for k, v in req.items():
                self.report.add(k, v)
        self.report.set_status(Report.ERROR)
        self.report.error(msg)

    def save_report_to_disc(self):
        try:
            with open('{}/{}_{}.json'.format(self.report_dir, self.test_number, time()), 'wb') as report_dump_file:
                report_dump_file.write(json.dumps(self.report.to_dict()))
        except Exception as e:
            self.logger.error(
                'Failed to save report "{}" to {} because: {}'
                    .format(self.report.to_dict(), self.report_dir, e)
            )

    def transmit(self, **kwargs):
        try:
            _req_url = list()
            for url_part in self.base_url, kwargs['url']:
                _req_url.append(url_part.strip('/'))
            kwargs['url'] = '/'.join(_req_url)
            if kwargs.get('path_variables'):
                kwargs['url'] = self.expand_path_variables(kwargs.get('path_variables'), kwargs['url'])
                kwargs.pop('path_variables')
            print("Request:")
            _return = requests.request(**kwargs)
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

    def expand_path_variables(self, params, url_chars):
        """
        Expands path variables:
        Example:
        http://localhost:8080/ingest/v1/catalog/{catalogid}/layer/{layerid}, {layerid: 11, catalogid:12} ->
        http://localhost:8080/ingest/v1/catalog/11/layer/12

        :param params: url variables, headers, request body from a swagger.json (
        :param url_chars: URL string without expanded path variables
        :returns URL string with expanded path variables
        """
        url_chars = list(url_chars)
        cleaned_url = []
        counter = 0
        while counter < len(url_chars):
            char = url_chars[counter]
            if char == '{':
                closing_position = "".join(url_chars)[counter:].find('}')
                value = url_chars[counter + 1:closing_position + counter]
                counter = closing_position + counter
                cleaned_url.extend(value)
            else:
                cleaned_url.append(char)
            counter = counter + 1
        cleaned_url = ''.join(cleaned_url)
        return cleaned_url

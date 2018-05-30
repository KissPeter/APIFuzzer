import json
from time import time

import requests
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
                self.logger.info('URL part: {}'.format(url_part))
                _req_url.append(url_part.strip('/'))
            for k, v in kwargs.get('path_variables', {}).items():
              _req_url.append(k)
            if kwargs.get('path_variables'):
                kwargs.pop('path_variables')
            kwargs.pop('url')
            self.logger.info('Request:{}'.format(kwargs))
            _return = requests.request(url='/'.join(_req_url), **kwargs)
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


def expand_path_variables(url_chars):
    """
    Expands path variables:
    Example:
    http://localhost:8080/ingest/v1/catalog/{catalogid}/layer/{layerid}, {layerid: 11, catalogid:12} ->
    http://localhost:8080/ingest/v1/catalog/11/layer/12

    :param params: url variables, headers, request body from a swagger.json (
    :param url_chars: URL string without expanded path variables
    :returns URL string with expanded path variables
    """
    url_chars = list(url_chars) if isinstance(url_chars, str) else ""
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

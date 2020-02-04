import json
import os
import re
import urllib.parse
from io import BytesIO
from time import time

import pycurl
import requests
from bitstring import Bits
from kitty.targets.server import ServerTarget

from apifuzzer.apifuzzer_report import Apifuzzer_Report as Report
from apifuzzer.utils import set_class_logger, try_b64encode


class Return():
    pass


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
        self.resp_headers = dict()

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
        _header = requests.utils.default_headers()
        _header.update(
            {
                'User-Agent': 'APIFuzzer',
            }
        )
        if isinstance(fuzz_header, dict):
            for k, v in fuzz_header.items():
                fuzz_header_name = k.split('|')[-1]
                self.logger.debug('Adding fuzz header: {}->{}'.format(fuzz_header_name, v))
                _header[fuzz_header_name] = v
        if isinstance(self.auth_headers, list):
            for auth_header_part in self.auth_headers:
                _header.update(auth_header_part)
        else:
            _header.update(self.auth_headers)
        return _header

    def report_add_basic_msg(self, msg):
        self.report.set_status(Report.FAILED)
        self.logger.warning(msg)
        self.report.failed(msg)

    def header_function(self, header_line):
        header_line = header_line.decode('iso-8859-1')
        if ':' not in header_line:
            return
        name, value = header_line.split(':', 1)
        self.resp_headers[name.strip().lower()] = value.strip()

    def format_pycurl_url(self, url):
        self.logger.debug('URL to process: %s', url)
        _dummy_curl = pycurl.Curl()
        url_fields = url.split('/')
        _tmp_url_list = list()
        for part in url_fields:
            self.logger.debug('Processing URL part: {}'.format(part))
            iteration = 0
            while True:
                iteration = iteration + 1
                try:
                    _test_list = list()
                    _test_list = _tmp_url_list[::]
                    _test_list.append(part)
                    _dummy_curl.setopt(pycurl.URL, '/'.join(_test_list))
                    self.logger.debug('Adding %s to the url: %s', part, _tmp_url_list)
                    _tmp_url_list.append(part)
                    break
                except (UnicodeEncodeError, ValueError) as e:
                    self.logger.debug('{} Problem adding ({}) to the url. Issue was:{}'.format(iteration, part, e))
                    if len(part):
                        self.logger.debug('Removing last character from part, current length: %s', len(part))
                        part = part[:-1]
                    else:
                        self.logger.info('The whole url part was removed, using empty string instead')
                        _tmp_url_list.append("")
                        break
                # except Exception as e:
                #   self.logger.exception(e)
        _return = '/'.join(_tmp_url_list)
        self.logger.info('URL to be used: %s', _return)
        return _return

    def format_pycurl_header(self, headers):
        """
        Pycurl and other http clients are picky, so this function tries to put everyting into the field as it can.
        :param headers: http headers
        :return: http headers
        :rtype: list of dicts
        """
        _dummy_curl = pycurl.Curl()
        _tmp = dict()
        _return = list()
        for k, v in headers.items():
            original_value = v
            iteration = 0
            chop_left = True
            chop_right = True
            while True:

                iteration = iteration + 1
                try:
                    _dummy_curl.setopt(pycurl.HTTPHEADER, ['{}: {}'.format(k, v).encode()])
                    _tmp[k] = v
                    break
                except ValueError as e:
                    self.logger.debug('{} Problem at adding {} to the header. Issue was:{}'.format(iteration, k, e))
                    if len(v):
                        if chop_left:
                            self.logger.debug('Removing first character from value, current length: %s', len(v))
                            v = v[1:]
                            if len(v) == 0:
                                chop_left = False
                                v = original_value
                        elif chop_right:
                            self.logger.debug('Removing last character from value, current length: %s', len(v))
                            v = v[:-1]
                            if len(v) == 1:
                                chop_left = False
                    else:
                        self.logger.info('The whole header value was removed, using empty string instead')
                        _tmp[k] = ""
                        break
        for k, v in _tmp.items():
            _return.append('{}: {}'.format(k, v).encode())
        return _return

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
            for param in ['path_variables', 'params']:  # todo: params are querystrings
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
                request_url, method, json.dumps(dict(kwargs.get('headers', {})), indent=2), kwargs.get('data')))
            self.report.set_status(Report.PASSED)
            self.report.add('request_url', request_url)
            self.report.add('request_method', method)
            self.report.add('request_headers', json.dumps(dict(kwargs.get('headers', {}))))
            try:
                resp_buff_hdrs = BytesIO()
                resp_buff_body = BytesIO()
                _curl = pycurl.Curl()
                b = BytesIO()
                if request_url.startswith('https'):
                    _curl.setopt(pycurl.SSL_OPTIONS, pycurl.SSLVERSION_TLSv1_2)
                    _curl.setopt(pycurl.SSL_VERIFYPEER, False)
                    _curl.setopt(pycurl.SSL_VERIFYHOST, False)
                _curl.setopt(pycurl.VERBOSE, True)
                _curl.setopt(pycurl.TIMEOUT, 10)
                _curl.setopt(pycurl.URL, self.format_pycurl_url(request_url))
                _curl.setopt(pycurl.HEADERFUNCTION, self.header_function)
                _curl.setopt(pycurl.HTTPHEADER, self.format_pycurl_header(kwargs.get('headers', {})))
                _curl.setopt(pycurl.COOKIEFILE, "")
                _curl.setopt(pycurl.USERAGENT, 'APIFuzzer')
                _curl.setopt(pycurl.POST, len(kwargs.get('data', {}).items()))
                _curl.setopt(pycurl.CUSTOMREQUEST, method)
                _curl.setopt(pycurl.POSTFIELDS, urllib.parse.urlencode(kwargs.get('data', {})))
                _curl.setopt(pycurl.HEADERFUNCTION, resp_buff_hdrs.write)
                _curl.setopt(pycurl.WRITEFUNCTION, resp_buff_body.write)
                for retries in reversed(range(3)):
                    try:
                        _curl.perform()
                    except Exception as e:
                        # pycurl.error usually
                        self.logger.error('{}: {}'.format(e.__class__.__name__, e))
                        if retries:
                            self.logger.error('Retrying... ({})'.format(retries))
                        else:
                            raise e
                _return = Return()
                _return.status_code = _curl.getinfo(pycurl.RESPONSE_CODE)
                _return.headers = self.resp_headers
                _return.content = b.getvalue()
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
                self.report_add_basic_msg('Failed to parse http response code')
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
            self.logger.error(
                'Failed to save report "{}" to {} because: {}'.format(self.report.to_dict(), self.report_dir, e))

    def expand_path_variables(self, url, path_parameters):
        if not isinstance(path_parameters, dict):
            self.logger.warn('Path_parameters {} does not in the desired format,received: {}'
                             .format(path_parameters, type(path_parameters)))
            return url
        _temporally_url_list = list()
        for path_key, path_value in path_parameters.items():
            self.logger.debug('Processing: path_key: {} , path_variable: {}'.format(path_key, path_value))
            path_parameter = path_key.split('|')[-1]
            url_path_paramter = '{%PATH_PARAM%}'.replace('%PATH_PARAM%', path_parameter)
            splitter = '({})'.format(path_parameter)
            url_list = re.split(splitter, url)
            self.logger.debug('URL split: {} with: {}'.format(url_list, splitter))
            if len(url_list) == 1:
                self.logger.warn('{} was not in the url: {}, adding it'.format(url_path_paramter, url))
                url_list.extend(['/', url_path_paramter])
            for url_part in url_list:
                self.logger.debug('Processing url part: {}'.format(url_part))
                if url_part == url_path_paramter:
                    self.logger.debug('Replace path parameter marker ({}) with fuzz value: {}'
                                      .format(url_path_paramter, path_value))
                    _temporally_url_list.append(path_value)
                else:
                    _temporally_url_list.append(url_part)
        _url = "".join(_temporally_url_list)
        self.logger.info('Compiled url in {}, out: {}'.format(url, _url))
        return _url.replace("{", "").replace("}", "").replace("+", "/")

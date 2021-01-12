import pycurl
import requests

from apifuzzer.fuzz_utils import container_name_to_param
from apifuzzer.utils import get_logger
from apifuzzer.version import get_version


class FuzzerTargetBase:

    def __init__(self, auth_headers):
        self._last_sent_request = None
        self.auth_headers = auth_headers
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info('Logger initialized')
        self.resp_headers = dict()
        self.chop_left = True
        self.chop_right = True

    def compile_headers(self, fuzz_header=None):
        """
        Using the fuzzer headers plus the header(s) defined at cli parameter this puts together a dict which will be
        used at the reques
        :type fuzz_header: list, dict, None
        """
        _header = requests.utils.default_headers()
        _header.update(
            {
                'User-Agent': get_version(),
            }
        )
        if isinstance(fuzz_header, dict):
            for k, v in fuzz_header.items():
                fuzz_header_name = container_name_to_param(k)
                self.logger.debug('Adding fuzz header: {}->{}'.format(fuzz_header_name, v))
                _header[fuzz_header_name] = v
        if isinstance(self.auth_headers, list):
            for auth_header_part in self.auth_headers:
                _header.update(auth_header_part)
        else:
            _header.update(self.auth_headers)
        return _header

    def header_function(self, header_line):
        header_line = header_line.decode('iso-8859-1')
        if ':' not in header_line:
            return
        name, value = header_line.split(':', 1)
        self.resp_headers[name.strip().lower()] = value.strip()

    @staticmethod
    def dict_to_query_string(query_strings):
        """
        Transforms dictionary to query string format
        :param query_strings: dictionary
        :type query_strings: dict
        :return: query string
        :rtype: str
        """
        _tmp_list = list()
        for query_string_key in query_strings.keys():
            _tmp_list.append('{}={}'.format(query_string_key, query_strings[query_string_key]))
        return '?' + '&'.join(_tmp_list)

    def format_pycurl_query_param(self, url, query_params):
        """
        Prepares fuzz query string by removing parts if necessary
        :param url: url used only to provide realistic url for pycurl
        :type url: str
        :param query_params: query strings in dict format
        :type query_params: dict
        :rtype: str
        """
        _dummy_curl = pycurl.Curl()
        _tmp_query_params = dict()
        for k, v in query_params.items():
            original_value = v
            iteration = 0
            self.chop_left = True
            self.chop_right = True
            while True:
                iteration = iteration + 1
                _test_query_params = _tmp_query_params.copy()
                _query_param_name = container_name_to_param(k)
                _test_query_params[_query_param_name] = v
                try:
                    _dummy_curl.setopt(pycurl.URL, '{}{}'.format(url, self.dict_to_query_string(_test_query_params)))
                    _tmp_query_params[_query_param_name] = v
                    break
                except (UnicodeEncodeError, ValueError) as e:
                    self.logger.debug('{} Problem adding ({}) as query param. Issue was:{}'.format(iteration, k, e))
                    if len(v):
                        v = self.chop_fuzz_value(original_fuzz_value=original_value, fuzz_value=v)
                    else:
                        self.logger.info('The whole query param was removed, using empty string instead')
                        _tmp_query_params[_query_param_name] = ""
                        break
                except Exception as e:  # pylint: disable=broad-exception
                    self.logger.error('Unexpected exception ({}) while processing: {}'.format(e, k))
        self.logger.warning('Returning: {}'.format(_tmp_query_params))
        return self.dict_to_query_string(_tmp_query_params)

    def format_pycurl_url(self, url):
        """
        Prepares fuzz URL for pycurl removing elements if necessary
        :param url: URL string prepared earlier
        :type url: str
        :return: pycurl compliant URL
        """
        self.logger.debug('URL to process: %s', url)
        _dummy_curl = pycurl.Curl()
        url_fields = url.split('/')
        _tmp_url_list = list()
        for part in url_fields:
            self.logger.debug('Processing URL part: {}'.format(part))
            original_value = part
            iteration = 0
            self.chop_left = True
            self.chop_right = True
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
                        part = self.chop_fuzz_value(original_fuzz_value=original_value, fuzz_value=part)
                    else:
                        self.logger.info('The whole url part was removed, using empty string instead')
                        _tmp_url_list.append("-")
                        break
        _return = '/'.join(_tmp_url_list)
        self.logger.info('URL to be used: %s', _return)
        return _return

    def chop_fuzz_value(self, original_fuzz_value, fuzz_value):
        """
        Prepares fuzz parameter for pycurl removing elements if necessary
        :param original_fuzz_value: original value of the filed
        :param fuzz_value: value modified in the previous run
        :return: fuzz value after chopping
        """
        if self.chop_left:
            self.logger.debug('Remove first character from value, current length: %s', len(fuzz_value))
            fuzz_value = fuzz_value[1:]
            if len(fuzz_value) == 0:
                self.chop_left = False
                fuzz_value = original_fuzz_value
        elif self.chop_right:
            self.logger.debug('Remove last character from value, current length: %s', len(fuzz_value))
            fuzz_value = fuzz_value[:-1]
            if len(fuzz_value) == 1:
                self.chop_left = False
        return fuzz_value

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
            self.chop_left = True
            self.chop_right = True
            while True:

                iteration = iteration + 1
                try:
                    _dummy_curl.setopt(pycurl.HTTPHEADER, ['{}: {}'.format(k, v).encode()])
                    _tmp[k] = v
                    break
                except ValueError as e:
                    self.logger.debug('{} Problem at adding {} to the header. Issue was:{}'.format(iteration, k, e))
                    if len(v):
                        v = self.chop_fuzz_value(original_fuzz_value=original_value, fuzz_value=v)
                    else:
                        self.logger.info('The whole header value was removed, using empty string instead')
                        _tmp[k] = ""
                        break
        for k, v in _tmp.items():
            _return.append('{}: {}'.format(k, v).encode())
        return _return

    def expand_path_variables(self, url, path_parameters):
        if not isinstance(path_parameters, dict):
            self.logger.warning('Path_parameters {} does not in the desired format,received: {}'
                                .format(path_parameters, type(path_parameters)))
            return url
        formatted_url = url
        for path_key, path_value in path_parameters.items():
            self.logger.debug('Processing: path_key: {} , path_variable: {}'.format(path_key, path_value))
            path_parameter = container_name_to_param(path_key)
            url_path_parameter = '{%PATH_PARAM%}'.replace('%PATH_PARAM%', path_parameter)
            tmp_url = formatted_url.replace(url_path_parameter, path_value)
            if tmp_url == formatted_url:
                self.logger.warning('{} was not in the url: {}, adding it'.format(url_path_parameter, url))
                tmp_url += '&{}={}'.format(path_parameter, path_value)
            formatted_url = tmp_url
        self.logger.info('Compiled url in {}, out: {}'.format(url, formatted_url))
        return formatted_url.replace("{", "").replace("}", "").replace("+", "/")

    @staticmethod
    def fix_data(data):
        new_data = {}
        for data_key, data_value in data.items():
            new_data[container_name_to_param(data_key)] = data_value
        return new_data

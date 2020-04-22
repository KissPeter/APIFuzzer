import json
import logging
import os
from base64 import b64encode
from binascii import Error
from io import BytesIO
from logging import Formatter
from logging.handlers import SysLogHandler
from random import randint

import pycurl
from bitstring import Bits
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

from apifuzzer.custom_fuzzers import RandomBitsField


def get_field_type_by_method(http_method):
    fields = {
        'GET': 'params',
        'POST': 'data',
        'PUT': 'data'
    }
    return fields.get(http_method, 'data')


def get_fuzz_type_by_param_type(fuzz_type):
    # https://kitty.readthedocs.io/en/latest/data_model/big_list_of_fields.html#atomic-fields
    # https://swagger.io/docs/specification/data-models/data-types/
    string_types = [RandomBitsField]
    number_types = [RandomBitsField]
    types = {
        'integer': number_types,
        'float': number_types,
        'double': number_types,
        'int32': number_types,
        'int64': number_types,
        'number': number_types,
        'string': string_types,
        'email': string_types,
        'uuid': string_types,
        'uri': string_types,
        'hostname': string_types,
        'ipv4': string_types,
        'ipv6': string_types,
        'boolean': string_types
    }
    fuzzer_list = types.get(fuzz_type, string_types)
    return fuzzer_list[randint(0, len(fuzzer_list) - 1)]


def get_sample_data_by_type(param_type):
    types = {
        u'name': '012',
        u'string': 'asd',
        u'integer': 1,
        u'number': 667.5,
        u'boolean': False,
        u'array': [1, 2, 3]  # transform_data_to_bytes complains when this array contains strings.
    }
    return types.get(param_type, b'\x00')


def set_logger(level='warning', basic_output=False):
    fmt = '%(process)d [%(levelname)s] %(name)s: %(message)s'
    if basic_output:
        logging.basicConfig(format=fmt)
        logger = logging.getLogger()
    else:
        logger = logging.getLogger()
        if not len(logger.handlers):
            handler = logging.StreamHandler()
            if os.path.exists('/dev/log'):
                handler = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_LOCAL2)
            handler.setFormatter(Formatter('%(process)d [%(levelname)s] %(name)s: %(message)s'))
            logger.addHandler(handler)
    logger.setLevel(level=level.upper())
    return logger


def transform_data_to_bytes(data_in):
    if isinstance(data_in, float):
        return bytes(int(data_in))
    elif isinstance(data_in, str):
        return bytes(data_in, 'utf-16')
    elif isinstance(data_in, Bits):
        return data_in.tobytes()
    else:
        return bytes(data_in)


def set_class_logger(class_name):
    class_name.logger = logging.getLogger(class_name.__class__.__name__)
    return class_name


def try_b64encode(data_in):
    try:
        return b64encode(data_in)
    except (TypeError, Error):
        return data_in


def container_name_to_param(container_name):
    return container_name.split('|')[-1]


def init_pycurl(debug=False):
    """
    Provides an instances of pycurl with basic configuration
    :return: pycurl instance
    """
    _curl = pycurl.Curl()
    _curl.setopt(pycurl.SSL_OPTIONS, pycurl.SSLVERSION_TLSv1_2)
    _curl.setopt(pycurl.SSL_VERIFYPEER, False)
    _curl.setopt(pycurl.SSL_VERIFYHOST, False)
    _curl.setopt(pycurl.VERBOSE, debug)
    _curl.setopt(pycurl.TIMEOUT, 10)
    _curl.setopt(pycurl.COOKIEFILE, "")
    _curl.setopt(pycurl.USERAGENT, 'APIFuzzer')
    return _curl


def download_file(url, dst_file):
    _curl = init_pycurl()
    buffer = BytesIO()
    _curl = pycurl.Curl()
    _curl.setopt(_curl.URL, url)
    _curl.setopt(_curl.WRITEDATA, buffer)
    _curl.perform()
    _curl.close()
    buffer.seek(0)
    with open(dst_file, 'wb') as tmp_file:
        tmp_file.write(buffer.getvalue())
    buffer.close()


def save_api_definition(url, temp_file):
    download_file(url, temp_file)
    return get_api_definition_from_file(temp_file)


def get_api_definition_from_file(src_file):
    try:
        with open(src_file, mode='rb') as f:
            api_definition = f.read()
        try:
            return json.loads(api_definition.decode('utf-8'))
        except ValueError as e:
            print('Failed to load input as JSON, maybe YAML?')
        try:
            yaml = YAML(typ='safe')
            return yaml.load(api_definition)
        except (TypeError, ScannerError) as e:
            print('Failed to load input as YAML:{}'.format(e))
            raise e
    except Exception:
        print('Failed to parse input file, exit')
        exit()

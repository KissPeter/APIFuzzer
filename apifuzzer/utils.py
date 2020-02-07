import logging
import os
from base64 import b64encode
from binascii import Error
from logging import Formatter
from logging.handlers import SysLogHandler
from random import randint

from bitstring import Bits

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
        u'array': [1, 2, 3] # transform_data_to_bytes complains when this array contains strings.
    }
    return types.get(param_type, b'\x00')


def set_logger(level='warning', basic_output=False):
    fmt = '%(process)d [%(levelname)s] %(name)s: %(message)s'
    if (basic_output):
        logging.basicConfig(format=fmt)
        logger = logging.getLogger()
    else:
        handler = logging.StreamHandler()
        if os.path.exists('/dev/log'):
            handler = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_LOCAL2)
        handler.setFormatter(Formatter('%(process)d [%(levelname)s] %(name)s: %(message)s'))
        logger = logging.getLogger()
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

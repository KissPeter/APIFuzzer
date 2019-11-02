import logging
import os
from base64 import b64encode
from logging import Formatter
from logging.handlers import SysLogHandler

from bitstring import Bits
from binascii import Error


from apifuzzer.custom_fuzzers import RandomBitsField


def get_field_type_by_method(http_method):
    fields = {
        'GET': 'params',
        'POST': 'data',
        'PUT': 'data'
    }
    return fields.get(http_method, 'data')


def get_fuzz_type_by_param_type(fuzz_type):
    # TODO we should have a shallow and a deep scan. This could be the difference
    # TODO get mutation according to a field type
    return RandomBitsField


def get_sample_data_by_type(param_type):
    types = {
        u'name': '012',
        u'string': 'asd',
        u'integer': 1,
        u'number': 667.5,
        u'boolean': False,
        u'array': ['a', 'b', 'c'],
        # TODO sample object
    }
    return types.get(param_type, 'asd')


def set_logger(level='warning'):
    handler = logging.StreamHandler()
    if os.path.exists('/dev/log'):
        handler = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_LOCAL2)
    handler.setFormatter(Formatter('%(process)d [%(levelname)s] %(name)s: %(message)s'))
    logger = logging.getLogger()
    logger.setLevel(level=level.upper())
    logger.addHandler(handler)
    return logger


def transform_data_to_bytes(data_in):
    # print('data_in: {}, type: {}'.format(data_in, type(data_in)))
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

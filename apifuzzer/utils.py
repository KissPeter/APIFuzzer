import logging
from logging import Formatter
from logging.handlers import SysLogHandler
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
    syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_LOCAL2)
    syslog.setFormatter(Formatter('%(process)d [%(levelname)s] %(name)s: %(message)s'))
    logger = logging.getLogger()
    logger.setLevel(level=level.upper())
    logger.addHandler(syslog)
    return logger


def set_class_logger(cls):
    cls.logger = logging.getLogger(cls.__class__.__name__)
    return cls

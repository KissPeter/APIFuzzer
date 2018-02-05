from logging import Formatter
from logging.handlers import SysLogHandler
from kitty.model import *
from custom_fuzzers import RandomBitsField


def get_field_type_by_method(http_method):
    fields = {
        'GET': 'params',
        'POST': 'data',
        'PUT': 'data'
    }
    return fields.get(http_method, 'data')


def get_fuzz_type_by_param_type(fuzz_type):
    # TODO we should have a shallow and a deep scan. This could be the difference
    return RandomBitsField


def get_sample_data_by_type(param_type):
    types = {
        'name': 012,
        'string': 'asd'
    }
    return types.get(param_type, 'asd')


def set_logger(level='warning'):
    syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_LOCAL2)
    syslog.setFormatter(Formatter('%(pathname)s [%(process)d]: %(levelname)s %(message)s'))
    logger = logging.getLogger('APIFuzzer')

    logger.setLevel(level=level.upper())
    logger.addHandler(syslog)
    return logger

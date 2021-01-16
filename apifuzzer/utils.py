import argparse
import json
import logging
import os
import sys
from base64 import b64encode
from binascii import Error
from io import BytesIO
from logging import Formatter
from logging.handlers import SysLogHandler
from random import SystemRandom
from typing import Optional

import pycurl
from bitstring import Bits

from apifuzzer.version import get_version

logger_name = 'APIFuzzer'


def secure_randint(minimum, maximum):
    """
    Provides solution for B311 "Standard pseudo-random generators are not suitable for security/cryptographic purposes."
    :param minimum: minimum value
    :type minimum: int
    :param maximum: maximum value
    :type maximum: int
    :return: random integer value between min and maximum
    """
    rand = SystemRandom()
    return rand.randrange(start=minimum, stop=maximum)


def set_logger(level='warning', basic_output=False):
    """
    Setup logger
    :param level: log level
    :type level: log level
    :param basic_output: If set to True, application logs to the terminal not to Syslog
    :type basic_output: bool
    :rtype logger
    """
    if level.lower() == 'debug':
        fmt = '%(process)d [%(levelname)7s] %(name)s [%(filename)s:%(lineno)s - %(funcName)20s ]: %(message)s'
    else:
        fmt = '%(process)d [%(levelname)7s] %(name)s: %(message)s'
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    if basic_output:
        handler = logging.StreamHandler(stream=sys.stdout)
    else:
        if os.path.exists('/dev/log'):
            handler = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_LOCAL2)
        else:
            handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(Formatter(fmt))
    logger.addHandler(handler)
    kitty_logger = logging.getLogger('kitty')
    kitty_logger.setLevel(level=logging.getLevelName(level.upper()))
    logger.setLevel(level=logging.getLevelName(level.upper()))
    logger.propagate = False
    return logger


def get_logger(name):
    """
    Configure the logger
    :param name: name of the new logger
    :return: logger object
    """
    logger = logging.getLogger(logger_name).getChild(name)
    return logger


def transform_data_to_bytes(data_in):
    """
    Transform data to bytes
    :param data_in: data to transform
    :type data_in: str, float, Bits
    :rtype: bytearray
    """
    if isinstance(data_in, float):
        return bytes(int(data_in))
    elif isinstance(data_in, str):
        return bytes(data_in, 'utf-16')
    elif isinstance(data_in, Bits):
        return data_in.tobytes()
    else:
        return bytes(data_in)


def try_b64encode(data_in):
    """
    Encode string to base64
    :param data_in: data to transform
    :type data_in: str
    :rtype str
    :return base64 string
    """
    try:
        return b64encode(data_in)
    except (TypeError, Error):
        return data_in


def container_name_to_param(container_name):
    """
    Split container name and provides name of related parameter
    :param container_name: container name
    :type container_name: str
    :return: param
    :rtype: str
    """
    return container_name.split('|')[-1]


def init_pycurl(debug=False):
    """
    Provides an instances of pycurl with basic configuration
    :param debug: confugres verbosity of http client
    :tpye debug: bool
    :return: pycurl instance
    """
    _curl = pycurl.Curl()
    _curl.setopt(pycurl.SSL_OPTIONS, pycurl.SSLVERSION_TLSv1_2)
    _curl.setopt(pycurl.SSL_VERIFYPEER, False)
    _curl.setopt(pycurl.SSL_VERIFYHOST, False)
    _curl.setopt(pycurl.VERBOSE, debug)
    _curl.setopt(pycurl.TIMEOUT, 10)
    _curl.setopt(pycurl.COOKIEFILE, "")
    _curl.setopt(pycurl.USERAGENT, get_version())
    return _curl


def download_file(url, dst_file):
    """
    Download file from the provided url to the defined file
    :param url: url to download from
    :type url: str
    :param dst_file: name of destination file
    :type dst_file: str
    :return: None
    """
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


def get_item(json_dict, json_path):
    """
    Get JSON item defined by path
    :param json_dict: JSON dict contains the item we are looking for
    :type json_dict: dict
    :param json_path: defines the place of the object
    :type json_path: list
    :return: dict
    """
    for item in json_path:
        json_dict = json_dict.get(item, {})
    return json_dict


def pretty_print(printable, limit=200):
    """
    Format json data for logging
    :param printable: json data to dump
    :type printable: dict, str
    :param limit: this amount of chars will be written
    :type limit: int
    :return: formatted string
    :rtype: str
    """
    if isinstance(printable, dict):
        return json.dumps(printable, sort_keys=True)[0:limit]
    elif isinstance(printable, str):
        return printable[:limit]
    else:
        return printable


def json_data(arg_string: Optional[str]) -> dict:
    """
    Transforms input string to JSON. Input must be dict or list of dicts like string
    :type arg_string: str
    :rtype dict
    """
    if isinstance(arg_string, dict) or isinstance(arg_string, list):  # support testing
        arg_string = json.dumps(arg_string)
    try:
        _return = json.loads(arg_string)
        if hasattr(_return, 'append') or hasattr(_return, 'keys'):
            return _return
        else:
            raise TypeError('not list or dict')
    except (TypeError, json.decoder.JSONDecodeError):
        msg = '%s is not JSON', arg_string
        raise argparse.ArgumentTypeError(msg)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1', 'True', 'T'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0', 'False', 'F'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

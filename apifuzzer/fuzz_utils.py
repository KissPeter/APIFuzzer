import json
import tempfile

from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

from apifuzzer.custom_fuzzers import RandomBitsField, Utf8Chars, UnicodeStrings
from apifuzzer.exceptions import FailedToParseFileException
from apifuzzer.utils import download_file, secure_randint


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
    string_types = [UnicodeStrings, RandomBitsField, Utf8Chars]
    number_types = [UnicodeStrings, RandomBitsField]
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
    return fuzzer_list[secure_randint(0, max(len(fuzzer_list) - 1, 1))]


def container_name_to_param(container_name):
    return container_name.split('|')[-1]


def get_api_definition_from_file(src_file, logger=None):
    if logger:
        print_func = logger
    else:
        print_func = print
    try:
        with open(src_file, mode='rb') as f:
            api_definition = f.read()
        # try loading as JSON first, then YAML
        try:
            return json.loads(api_definition.decode('utf-8'))
        except ValueError as e:
            print_func(f'Failed to load input ({src_file}) as JSON because ({e}), maybe YAML?')
        try:
            yaml = YAML(typ='safe')
            return yaml.load(api_definition.decode('utf-8'))
        except (TypeError, ScannerError) as e:
            print_func(f'Failed to load input ({src_file}) as YAML:{e}')
            raise e
    except (Exception, FileNotFoundError) as e:
        print_func(f'Failed to parse input file ({src_file}), because: ({e}) exit')
        raise FailedToParseFileException


def get_api_definition_from_url(url, temp_file=None, logger=None):
    if temp_file is None:
        temp_file = tempfile.NamedTemporaryFile().name
    download_file(url, temp_file)
    return get_api_definition_from_file(temp_file, logger=logger)


def get_base_url_form_api_src(url):
    """
    provides base url from api definition source url.
    :param url: url like https://example.com/api/v1/api.json
    :return: url like https://example.com/api/v1
    """
    splited_url = url.split('/')
    return "/".join(splited_url[:len(splited_url) - 1])

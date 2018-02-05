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
    # TODO get mutation according to a field type
    return RandomBitsField


def get_sample_data_by_type(param_type):
    types = {
        u'name': 012,
        u'string': 'asd',
        u'integer': 1,
        u'number': 667,
        u'boolean': False,
        u'array': ['a', 'b', 'c'],
        # TODO sample object
    }
    return types.get(param_type, 'asd')

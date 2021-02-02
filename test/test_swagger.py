from test.test_utils import BaseTest


class TestSwagger(BaseTest):

    def test_single_path_parameter(self):
        test_url = '/path_param'
        api_path = "/".join([test_url, '{integer_id}'])
        api_def = {
            "get": {
                "parameters": [
                    {
                        "name": "integer_id",
                        "in": "path",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    }

                ]
            }
        }
        last_call = self.fuzz_swagger_and_get_last_call(api_path, api_def)
        # last_call test field sample:
        # "req_path": "/path_param/\u001f/\u001c\u007f\u0000N@",
        last_value_sent = last_call['req_path'].replace(test_url, '')
        assert not isinstance(last_value_sent, int), last_value_sent
        self.repot_basic_check()

    def test_single_query_string(self):
        api_path = '/query'
        api_def = {
            "get": {
                "parameters": [
                    {
                        "name": "integer_id",
                        "in": "query",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    }

                ]
            }
        }
        # last_call test field sample:
        # 'http://127.0.0.1:5000/query?integer_id=%10'
        last_call = self.fuzz_swagger_and_get_last_call(api_path, api_def)
        _, last_value_sent = last_call['req_url'].split("=")
        assert not isinstance(last_value_sent, int), last_call['req_url']
        self.repot_basic_check()

    def test_multiple_query_strings(self):
        api_path = '/query_multiple_params'
        api_def = {
            "get": {
                "parameters": [
                    {
                        "name": "int_query_param1",
                        "in": "query",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    },
                    {
                        "name": "int_query_param2",
                        "in": "query",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    }
                ]
            }
        }
        last_call = self.fuzz_swagger_and_get_last_call(api_path, api_def)
        # last_call['req_url']
        # http://127.0.0.1:5000/query_multiple_params?int_query_param1=667.5&int_query_param2=%10
        _, query_string = last_call['req_url'].split("?", maxsplit=1)
        _, val_1, _, val_2 = query_string.replace('&', '=').split('=')
        assert float(val_1), 'last_qery_url: {}, value1: {}'.format(last_call['req_url'], val_1)
        assert not isinstance(val_2, int), 'last_qery_url: {}, value2: {}'.format(last_call['req_url'], val_2)
        self.repot_basic_check()

    def test_multiple_path_params(self):
        test_url = '/multiple_path_params'
        api_path = "/".join([test_url, '{int_path_param1}', '{int_path_param2}'])
        api_def = {
            "get": {
                "parameters": [
                    {
                        "name": "int_path_param1",
                        "in": "path",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    },
                    {
                        "name": "int_path_param2",
                        "in": "path",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    }
                ]
            }
        }
        last_call = self.fuzz_swagger_and_get_last_call(api_path, api_def)
        # last_call['req_path']
        # 'req_path': '/multiple_path_params/667.5/\x10'
        _, test_url_reported, param1, param2 = last_call['req_path'].split("/", maxsplit=3)
        assert test_url[1:] == test_url_reported, last_call['req_path']  # heading / shall be removed
        assert not isinstance(param1, int), 'req_path: {}, param1: {}'.format(last_call['req_url'], param1)
        assert not isinstance(param2, int), 'req_path: {}, param2: {}'.format(last_call['req_url'], param2)
        self.repot_basic_check()

    def test_v2_post_with_schema(self):
        api_path = '/post_param'
        api_def = {
            "post": {
                "parameters": [
                    {
                        "in": "body",
                        "name": "body",
                        "schema": {
                            "$ref": "#/definitions/schema_definition"
                        }
                    }
                ]
            }
        }
        schema = {
            "schema_definition": {
                "properties": {
                    "param_str": {
                        "type": "string"
                    },
                    "param_int": {
                        "type": "int"
                    }
                }
            }
        }
        last_call = self.fuzz_swagger_and_get_last_call(api_path, api_def, schema_definitions=schema)
        # "req_form": {
        #     "param_int": "\u0000",
        #     "param_str": "65Y"
        # },
        assert not isinstance(last_call['req_form']['param_int'], int), last_call
        self.repot_basic_check()

    def test_v2_header(self):
        api_path = '/v2_header'
        api_def = {
            "get": {
                "parameters": [
                    {
                        "name": "X-Test",
                        "in": "header",
                        "required": True,
                        "type": "number",
                        "format": "double"
                    }

                ]
            }
        }
        last_call = self.fuzz_swagger_and_get_last_call(api_path, api_def)
        last_value_sent = last_call['req_headers']['X-Test']
        assert not isinstance(last_value_sent, int), last_call
        self.repot_basic_check()

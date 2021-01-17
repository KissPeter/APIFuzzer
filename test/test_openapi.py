from test.test_utils import BaseTest


class TestOpenAPI(BaseTest):

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
        last_call = self.fuzz_openapi_and_get_last_call(api_path, api_def)

from test.test_utils import BaseTest


class TestOpenAPI(BaseTest):

    def test_v3_post_with_schema(self):
        api_path = '/v3_post'
        api_def = {
            "post": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/definitions/ItemDraft"
                            }
                        }
                    }
                }
            }
        }
        schema = {
            "ItemDraft": {
                "type": "object",
                "properties": {
                    "category_id": {
                        "type": "integer",
                    }
                }
            }
        }
        last_call = self.fuzz_openapi_and_get_last_call(api_path, api_def, schema_definitions=schema)
        # "req_form": {
        #     "param_int": "\u0000",
        #     "param_str": "65Y"
        # },
        assert not isinstance(last_call['req_form']['category_id'], int), last_call
        self.repot_basic_check()

from test.test_utils import BaseTest


class TestOpenAPI(BaseTest):
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

    def test_v3_post_with_schema_json_content_type(self):
        api_path = '/v3_post_json'
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
        last_call = self.fuzz_openapi_and_get_last_call(api_path, api_def, schema_definitions=self.schema)
        assert not isinstance(last_call['req_json']['category_id'], int), last_call
        assert last_call['req_headers']['Content-Type'] == 'application/json'
        self.repot_basic_check()

    def test_v3_post_with_schema_multiparm_formdata_content_type(self):
        api_path = '/v3_post_multipart'
        api_def = {
            "post": {
                "requestBody": {
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "$ref": "#/definitions/ItemDraft"
                            }
                        }
                    }
                }
            }
        }
        last_call = self.fuzz_openapi_and_get_last_call(api_path, api_def, schema_definitions=self.schema)
        assert not isinstance(last_call['req_form']['category_id'], int), last_call
        assert last_call['req_headers']['Content-Type'].startswith('multipart/form-data')
        self.repot_basic_check()

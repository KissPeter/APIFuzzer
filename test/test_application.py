#!/usr/bin/env python3
import json
from functools import wraps

from flask import Flask, request


class LastRequestData(object):

    def __init__(self):
        self.last_request_data = dict()

    def wipe_data(self):
        self.last_request_data = dict()

    def set_data(self, data=None):
        if data is not None:
            self.last_request_data.update(data)

    def get_data(self):
        try:
            return json.dumps(self.last_request_data, ensure_ascii=False, indent=2, sort_keys=True)
        except TypeError as e:
            return 'Error: {}, latest data: {}'.format(e, self.last_request_data)


def catch_custom_exception(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return "Test application exception: {}".format(e), 500

    return decorated_function


def extract(d):
    return {key: value for (key, value) in d.items()}


app = Flask(__name__)
last_request_data = LastRequestData()


@app.route('/path_param/<integer_id>', methods=['GET'])
@catch_custom_exception
def path_param(integer_id):
    return 'ID: {}'.format(int(integer_id))


@app.route('/multiple_path_params/<int_path_param1>/<int_path_param2>', methods=['GET'])
@catch_custom_exception
def transform(int_path_param1, int_path_param2):
    return 'int_path_param1: {}, int_path_param2: {}'.format(int(int_path_param1), int(int_path_param2))


@app.route('/query')
@catch_custom_exception
def query():
    return 'ID: {}'.format(int(request.args.get('integer_id')))


@app.route('/post_param')
@catch_custom_exception
def post_params():
    return 'ID: {}'.format(int(request.args.get('post_param')))


@app.route('/query_multiple_params')
@catch_custom_exception
def query_multiple_params():
    return 'ID: {}'.format(int(request.args.get('int_query_param2')))


@app.route('/post_param', methods=['POST'])
@catch_custom_exception
def post_param():
    return 'ID: {}'.format(int(request.form.get('param_int', 0)))


@app.route('/v3_post_json', methods=['POST'])
@catch_custom_exception
def v3_post_json():
    return 'ID: {}'.format(int(request.json.get('category_id', 0)))


@app.route('/v3_post_multipart', methods=['POST'])
@catch_custom_exception
def v3_post_multipart():
    return 'ID: {}'.format(int(request.form.get('category_id', 0)))


@app.route('/v2_header', methods=['GET'])
@catch_custom_exception
def v2_header():
    return 'ID: {}'.format(int(request.headers.get('X-Test', 0)))


@app.route('/last_call', methods=['GET'])
def last_call():
    _return = last_request_data.get_data()
    last_request_data.wipe_data()
    return _return


@app.after_request
def log_the_status_code(response):
    last_request_data.set_data({
        'resp_body': str(response.get_data()),
        'resp_headers': extract(response.headers),
        'resp_status': response.status_code,
        'req_path': request.path,
        'req_url': request.url,
        'req_method': request.method,
        'req_headers': extract(request.headers),
        'req_form': extract(request.form),
        'req_form2': request.form.to_dict(flat=False),
        'req_json': request.json,
        'req_data': request.data.decode(encoding='UTF-8')
    })
    return response


if __name__ == '__main__':
    app.run(debug=True)

#!/usr/bin/env python3
from functools import wraps
import json
from flask import Flask,  request
from werkzeug.routing import Rule

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
app.url_map.add(Rule('/', defaults={'path': ''}, endpoint='index'))
app.url_map.add(Rule('/<path:path>', endpoint='index'))
last_request_data = LastRequestData()


@app.route('/exception/<integer_id>', methods=['GET'])
@catch_custom_exception
def transform(integer_id):
    return 'ID: {}'.format(int(integer_id))


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
        'req_json': request.json,
        'req_data': request.data.decode(encoding='UTF-8')
    })
    return response


if __name__ == '__main__':
    app.run(debug=True)

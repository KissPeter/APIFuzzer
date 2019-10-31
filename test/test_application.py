#!/usr/bin/env python2.7
import time
from functools import wraps

from flask import Flask, jsonify, request
from werkzeug.routing import Rule


class LastRequestData(object):

    def __init__(self):
        self.last_request_data = dict()

    def set_data(self, data=None):
        self.last_request_data = data

    def get_data(self):
        return self.last_request_data


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
    _return = jsonify(last_request_data.get_data())
    last_request_data.set_data({})
    return _return


@app.endpoint('index')
def save_request(path):
    last_request = {
        'status': request.args.get('status'),
        'time': time.time(),
        'path': request.path,
        'script_root': request.script_root,
        'url': request.url,
        'base_url': request.base_url,
        'url_root': request.url_root,
        'method': request.method,
        'headers': extract(request.headers),
        'data': request.data.decode(encoding='UTF-8'),
        'host': request.host,
        'args': extract(request.args),
        'form': extract(request.form),
        'json': request.json,
        'cookies': extract(request.cookies)
    }
    last_request_data.set_data(last_request)
    return ''


if __name__ == '__main__':
    app.run(debug=True)

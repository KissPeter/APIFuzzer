#!/usr/bin/env python2.7
from werkzeug.exceptions import HTTPException
from flask import Flask, jsonify, request
from werkzeug.routing import Rule

import time


class LastRequestData(object):

    def __init__(self):
        self.last_request_data = dict()

    def set_data(self, data=None):
        self.last_request_data = data

    def get_data(self):
        return self.last_request_data


class InternalError(HTTPException):
    code = 500


def extract(d):
    return {key: value for (key, value) in d.items()}


app = Flask(__name__)
app.register_error_handler(500, InternalError)
app.url_map.add(Rule('/', defaults={'path': ''}, endpoint='index'))
app.url_map.add(Rule('/<path:path>', endpoint='index'))
last_request_data = LastRequestData()


@app.route('/exception/<integer_id>', methods=['GET'])
def transform(integer_id):
    try:
        _integer_id = int(integer_id)
    except ValueError:
        raise InternalError('Failed to convert %s to int', integer_id)
    return 'ID: {}'.format(_integer_id)


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

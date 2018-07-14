#!/usr/bin/env python3.6
from flask import Flask
from werkzeug.exceptions import HTTPException


class InternalError(HTTPException):
    code = 500

app = Flask(__name__)
app.register_error_handler(500, InternalError)


@app.route('/exception/<integer_id>', methods=['GET'])
def transform(integer_id):
    try:
        _integer_id = int(integer_id)
    except ValueError:
        raise InternalError('Failed to convert {} to int'.format(integer_id))
    return 'ID: {}'.format(_integer_id)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return 'No match for {}'.format(path)


if __name__ == '__main__':
    app.run()

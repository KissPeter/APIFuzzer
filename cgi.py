"""Compatibility shim for Python 3.13+ where stdlib cgi module was removed.

json-ref-dict still imports cgi.parse_header(); this minimal implementation
keeps that dependency working without changing third-party code.
"""

from email.message import Message


def parse_header(line):
    """Return (main_value, params) similarly to the removed cgi.parse_header."""
    msg = Message()
    msg["content-type"] = line
    main = msg.get_content_type()
    params = {k.lower(): v for k, v in msg.get_params(header="content-type")[1:]}
    return main, params


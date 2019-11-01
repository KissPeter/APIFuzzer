from __future__ import print_function

from kitty.model import Static, Template, Container


class BaseTemplate(object):

    def __init__(self, name):
        self.name = name
        self.method = None
        self.url = None
        self.params = list()
        self.data = list()
        self.headers = list()
        self.path_variables = list()
        self.cookies = list()
        """
        Possible paramters from request docs:
        :param method: method for the new :class:`Request` object.
        :param bytes url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`.
        :param json: (optional) json data to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        """

    def compile_template(self):
        _url = Static(name='url', value=self.url)
        # _url = Static(name='url', value=self.url, encoder=ENC_STR_UTF8)
        _method = Static(name='method', value=self.method)
        # _method = Static(name='method', value=self.method, encoder=ENC_STR_UTF8)
        template = Template(name=self.name, fields=[_url, _method])
        if list(self.params):
            template.append_fields([Container(name='params', fields=self.params)])
        if list(self.headers):
            template.append_fields([Container(name='headers', fields=self.headers)])
        if list(self.data):
            template.append_fields([Container(name='data', fields=self.data)])
        if list(self.path_variables):
            template.append_fields([Container(name='path_variables', fields=self.path_variables)])
        if list(self.cookies):
            template.append_fields([Container(name='cookies', fields=self.cookies)])
        return template

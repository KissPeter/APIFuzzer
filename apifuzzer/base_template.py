from __future__ import print_function

from kitty.model import Static, Template, Container


class BaseTemplate(object):

    def __init__(self, name, strategy, logger):
        self.name = name
        self.method = None
        self.url = None
        self.params = list()
        self.data = list()
        self.headers = list()
        self.path_variables = list()
        self.query = list()
        self.cookies = list()
        self.field_to_param = {
            'params': self.params,
            'headers': self.headers,
            'data': self.data,
            'path_variables': self.path_variables,
            'cookies': self.cookies,
            'query': self.query
        }
        self.strategy = strategy
        self.logger = logger
        """
        Possible paramters from request docs:
        :param method: method for the new :class:`Request` object.
        :param bytes url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`.
        :param query: (optional) query stringsto send in url of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        """

    def strategy_default(self, template):
        for name, field in self.field_to_param.items():
            if list(field):
                template.append_fields([Container(name=name, fields=field)])

    def strategy_all_params_at_once(self, template):
        for name, field in self.field_to_param.items():
            if list(field):
                template.append_fields([Container(name=name, fields=field)])

    def compile_template(self):
        _url = Static(name='url', value=self.url)
        _method = Static(name='method', value=self.method)
        template = Template(name=self.name, fields=[_url, _method])
        switcher = {
            'default': self.strategy_default,
            'all_params_at_once': self.strategy_all_params_at_once,
        }
        strategy = switcher.get(self.strategy, self.strategy_default)
        
        strategy(template)
        return template

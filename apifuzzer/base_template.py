from kitty.core import KittyException
from kitty.model import Static, Template, Container

from apifuzzer.utils import get_logger


class BaseTemplate(object):

    def __init__(self, name):
        self.logger = get_logger(self.__class__.__name__)
        self.name = name
        self.content_type = ''
        self.method = None
        self.url = None
        self.params = set()
        self.data = set()
        self.headers = set()
        self.path_variables = set()
        self.query = set()
        self.cookies = set()
        self.field_to_param = {
            'params': self.params,
            'headers': self.headers,
            'data': self.data,
            'path_variables': self.path_variables,
            'cookies': self.cookies,
            'query': self.query,
            'content_type': self.content_type
        }
        """
        Possible paramters from request docs:
        :param method: method for the new :class:`Request` object.
        :param bytes url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary, bytes, or file-like object to send in the body of the :class:`Request`.
        :param query: (optional) query strings to send in url of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        """

    def get_stat(self):
        total = 0
        for field in self.field_to_param.values():
            total += len(field)
        self.logger.info(f'Template size: {total}, content: {self.field_to_param}')
        return total

    def compile_template(self):
        _url = Static(name='url', value=self.url)
        _method = Static(name='method', value=self.method)
        template = Template(name=self.name, fields=[_url, _method])
        for name, field in self.field_to_param.items():
            if list(field):
                try:
                    template.append_fields([Container(name=name, fields=field)])
                except KittyException as e:
                    self.logger.warning('Failed to add {} because {}, continue processing...'.format(name, e))
        return template

    def get_content_type(self):
        return self.content_type

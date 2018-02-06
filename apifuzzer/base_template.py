from __future__ import print_function

from kitty.model import Static, Template, Container


class BaseTemplate(object):
    url = None
    method = None
    parameters = None
    headers = None
    data = None
    path_variables = None

    def compile_template(self):
        _url = Static(name='url', value=self.url.encode())
        _method = Static(name='method', value=self.method.encode())
        template = Template(name='{}_{}'.format(self.url.replace('/', '_'), self.method), fields=[_url, _method])
        if self.parameters:
            template.append_fields([Container(name='parameters', fields=self.parameters)])
        if self.headers:
            template.append_fields([Container(name='headers', fields=self.headers)])
        if self.data:
            template.append_fields([Container(name='data', fields=self.data)])
        if self.path_variables:
            template.append_fields([Container(name='path_variables', fields=self.path_variables)])
        return template

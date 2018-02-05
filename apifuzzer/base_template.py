from __future__ import print_function
from kitty.model import Static, Template, Container
from utils import get_field_type_by_method


class BaseTemplate(object):
    url = None
    method = None
    headers = None
    fuzz_params = None

    def __init__(self):
        self.fuzz_place = None

    def compile_template(self):
        _url = Static(name='url', value=self.url.encode())
        _method = Static(name='method', value=self.method.encode())
        template = Template(name='{}_{}'.format(self.url.replace('/', '_'), self.method), fields=[_url, _method])
        self.fuzz_place = get_field_type_by_method(self.method)
        template.append_fields([Container(name='headers', fields=self.headers)])
        template.append_fields([Container(name='{}'.format(self.fuzz_place), fields=self.fuzz_params)])
        return template

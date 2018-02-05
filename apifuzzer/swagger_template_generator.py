from base_template import BaseTemplate
from utils import get_sample_data_by_type, get_fuzz_type_by_param_type
from template_generator_base import TemplateGenerator
from enum import Enum


class ParamTypes(Enum):
    PATH = 'path'
    QUERY = 'query'
    HEADER = 'header'
    COOKIE = 'cookie'
    BODY = 'body'
    FORM_DATA = 'formData'


class SwaggerTemplateGenerator(TemplateGenerator):
    def __init__(self, api_resources, logger):
        self.api_resources = api_resources
        self.logger = logger
        self.templates = list()

    def process_api_resources(self):
        for resource in self.api_resources['paths'].keys():
            print(resource)
            for method in self.api_resources['paths'][resource].keys():
                self.logger.debug(method)
                template = BaseTemplate()
                template.url = resource
                template.method = method.upper()
                params = list()
                headers = list()
                for param in self.api_resources['paths'][resource][method].get('parameters', []):
                    if param.get('in') in [ParamTypes.HEADER, ParamTypes.COOKIE]:
                        self.logger.info('{} - {} headers'.format(param['name'], param.get('in')))
                        list_to_add = headers
                    else:
                        self.logger.info('{} - headers'.format(param['name']))
                        list_to_add = params
                    fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                    list_to_add.append(
                        fuzz_type(
                            name=param['name'],
                            value=get_sample_data_by_type(param.get('type'))
                        )
                    )

                template.headers = headers
                template.fuzz_params = params
                self.templates.append(template)

    def compile_base_url(self):
        if 'http' in self.api_resources['schemes']:
            _protocol = 'http'
        else:
            _protocol = self.api_resources['schemes'][0]
        _base_url = '{}://{}{}'.format(
            _protocol,
            self.api_resources['host'],
            self.api_resources['basePath']
        )
        return _base_url

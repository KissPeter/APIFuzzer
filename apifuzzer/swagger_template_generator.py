from base_template import BaseTemplate
from template_generator_base import TemplateGenerator
from utils import get_sample_data_by_type, get_fuzz_type_by_param_type


class SwaggerTemplateGenerator(TemplateGenerator):
    def __init__(self, api_resources):
        self.api_resources = api_resources
        self.templates = list()

    def process_api_resources(self):
        for resource in self.api_resources['paths'].keys():
            print(resource)
            for method in self.api_resources['paths'][resource].keys():
                print(method)
                template = BaseTemplate()
                template.url = resource
                template.method = method.upper()
                template.parameters = list()
                template.headers = list()
                template.path_variables = list()
                for param in self.api_resources['paths'][resource][method].get('parameters', []):
                    print(param['name'])
                    # get parameter placement(in): path, query, header, cookie
                    # get parameter type: integer, string
                    # get format if present
                    if param['in'] == 'path':
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.path_variables.append(
                            fuzz_type(
                                name=param['name'],
                                value=get_sample_data_by_type(param.get('type'))
                            ))
                    elif param['in'] == 'header':
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.headers.append(
                            fuzz_type(
                                name=param['name'],
                                value=get_sample_data_by_type(param.get('type'))
                            ))
                    elif param['in'] == 'body':
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.data = fuzz_type(name=param['name'], value=get_sample_data_by_type(param.get('type')))
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

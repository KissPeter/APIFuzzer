from base_template import BaseTemplate
from utils import get_sample_data_by_type, get_fuzz_type_by_param_type
from template_generator_base import TemplateGenerator


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
                params = list()
                for param in self.api_resources['paths'][resource][method].get('parameters',[]):
                    print(param['name'])
                    fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                    params.append(
                        fuzz_type(
                            name=param['name'],
                            value=get_sample_data_by_type(param.get('type'))
                        )
                    )
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

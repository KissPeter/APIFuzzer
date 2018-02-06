from base_template import BaseTemplate
from template_generator_base import TemplateGenerator
from utils import get_sample_data_by_type, get_fuzz_type_by_param_type


class ParamTypes(object):
    PATH = 'path'
    QUERY = 'query'
    HEADER = 'header'
    COOKIE = 'cookie'
    BODY = 'body'
    FORM_DATA = 'formData'


class SwaggerTemplateGenerator(TemplateGenerator):
    def __init__(self, api_resources, logger):
        self.api_resources = api_resources
        self.templates = list()
        self.logger = logger

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
                    param_type = param.get('in')
                    if param_type == ParamTypes.PATH:
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.path_variables.append(
                            fuzz_type(
                                name=param['name'],
                                value=get_sample_data_by_type(param.get('type'))
                            ))
                    elif param_type == ParamTypes.HEADER or param_type == ParamTypes.COOKIE:
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.headers.append(
                            fuzz_type(
                                name=param['name'],
                                value=get_sample_data_by_type(param.get('type'))
                            ))
                    elif param_type == ParamTypes.QUERY:
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.parameters.append(
                            fuzz_type(
                                name=param['name'],
                                value=get_sample_data_by_type(param.get('type'))
                            ))
                    elif param_type == ParamTypes.BODY or param_type == ParamTypes.FORM_DATA:
                        fuzz_type = get_fuzz_type_by_param_type(param.get('type'))
                        template.data = fuzz_type(
                            name=param['name'],
                            value=get_sample_data_by_type(param.get('type'))
                        )
                    else:
                        # FIXMY doens't work due to some reason!!
                        print("azaza")
                        self.logger.error('Cant parse a definition from swagger.json: %s', param)
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

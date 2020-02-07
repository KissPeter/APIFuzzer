from apifuzzer.base_template import BaseTemplate
from apifuzzer.template_generator_base import TemplateGenerator
from apifuzzer.utils import get_sample_data_by_type, get_fuzz_type_by_param_type, transform_data_to_bytes


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
        self.logger.info('Logger initialized')

    @staticmethod
    def normalize_url(url_in):
        # Kitty doesn't support some characters as template name so need to be cleaned, but it is necessary, so
        # we will change back later
        return url_in.strip('/').replace('/', '+')

    def process_api_resources(self):
        for resource in self.api_resources['paths'].keys():
            normalized_url = self.normalize_url(resource)
            for method in self.api_resources['paths'][resource].keys():
                self.logger.info('Resource: {} Method: {}'.format(resource, method))
                template_container_name = '{}|{}'.format(normalized_url, method)
                template = BaseTemplate(name=template_container_name)
                template.url = normalized_url
                template.method = method.upper()
                self.logger.debug('Resource: {} Method: {}'.format(resource, method))
                for param in self.api_resources['paths'][resource][method].get('parameters', {}):
                    type = param.get('type')
                    format = param.get('format')
                    if format is not None:
                        fuzzer_type = format.lower()
                    elif type is not None:
                        fuzzer_type = type.lower()
                    else:
                        fuzzer_type = None
                    fuzz_type = get_fuzz_type_by_param_type(fuzzer_type)
                    sample_data = get_sample_data_by_type(param.get('type'))
                    # get parameter placement(in): path, query, header, cookie
                    # get parameter type: integer, string
                    # get format if present
                    param_type = param.get('in')
                    self.logger.debug('Resource: {} Method: {} Parameter: {}, Parameter type: {}, Sample data: {},'
                                      'Param name: {}'
                                      .format(resource, method, param, param_type, sample_data, param_name))
                    if param_type == ParamTypes.PATH:
                        template.path_variables.append(fuzz_type(name=param_name, value=str(sample_data)))
                    elif param_type == ParamTypes.HEADER:
                        template.headers.append(fuzz_type(name=param_name, value=transform_data_to_bytes(sample_data)))
                    elif param_type == ParamTypes.COOKIE:
                        template.cookies.append(fuzz_type(name=param_name, value=sample_data))
                    elif param_type == ParamTypes.QUERY:
                        template.params.append(fuzz_type(name=param_name, value=str(sample_data)))
                    elif param_type in [ParamTypes.BODY, ParamTypes.FORM_DATA]:
                        template.data.append(fuzz_type(name=param_name, value=transform_data_to_bytes(sample_data)))
                    else:
                        self.logger.error('Can not parse a definition from swagger.json: %s', param)
                self.templates.append(template)

    def compile_base_url(self, alternate_url):
        """
        :param alternate_url: alternate protocol and base url to be used instead of the one defined in swagger
        :type alternate_url: string
        """
        if alternate_url:
            _base_url = "/".join([alternate_url.strip('/'), self.api_resources.get('basePath', '').strip('/')])
        else:
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

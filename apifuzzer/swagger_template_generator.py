from apifuzzer.base_template import BaseTemplate
from apifuzzer.template_generator_base import TemplateGenerator
from apifuzzer.utils import get_sample_data_by_type, get_fuzz_type_by_param_type, transform_data_to_bytes, \
    get_api_definition_from_url, get_api_definition_from_file, get_item


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

    def get_properties_from_schema_definition(self, schema, element=None):
        self.logger.info('Getting {} from {}'.format([element, 'properties'], schema))
        return get_item(schema, '/'.join([element, 'properties']))

    def get_schema(self, param):
        """
        Processes schema referenced if request method should be POST and request should contain body
        :rtype: param section of api definition.
        Example:
            {
            "in": "body",
            "name": "body",
            "description": "Pet object that needs to be added to the store",
            "required": false,
            "schema": {
              "$ref": "#/definitions/Pet"
            }
        """
        schema_properties = None
        schema_ref = param.get('schema', {}).get('$ref')
        self.logger.debug('Processing param id {}, reference for schema: {}'.format(param.get('id'), schema_ref))
        if schema_ref.startswith('#'):
            self.logger.debug('Looking for reference in local file: {}'.format(schema_ref))
            schema_path = schema_ref.split('/')
            # dropping first element of the list as it defines it is local reference
            schema_path.pop(0)
            schema_definition = get_item(self.api_resources, schema_path)
            schema_properties = self.get_properties_from_schema_definition(schema_definition)
        elif schema_ref.startswith('http'):
            # https://swagger.io/docs/specification/using-ref/
            self.logger.debug('Looking for remote reference: {}'.format(schema_ref))
            resource_reference, item_location = schema_ref.split('#', 1)
            self.logger.info('Downloading resource from: {} and using {}'.format(resource_reference, item_location))
            schema_definition = get_api_definition_from_url(resource_reference)
            schema_properties = self.get_properties_from_schema_definition(schema_definition, item_location)
        elif schema_ref.startswith('//'):
            self.logger.debug('Not implemented import: {}'.format(schema_ref))
        else:
            file_reference, item_location = schema_ref.split('#', 1)
            self.logger.debug('It seems the schema is stored in local file? {}'.format(file_reference))
            schema_definition = get_api_definition_from_file(file_reference)
            schema_properties = self.get_properties_from_schema_definition(schema_definition, item_location)
        self.logger.info('Schema definition: {} discovered from {}'.format(schema_properties, param))
        return schema_properties

    def process_api_resources(self):
        self.logger.info('Start preparation')
        tmp_api_resource = self.api_resources['paths']
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
                    param_type = param.get('type')
                    param_format = param.get('format')
                    if param_format is not None:
                        fuzzer_type = param_format.lower()
                    elif param_type is not None:
                        fuzzer_type = param_type.lower()
                    else:
                        fuzzer_type = None
                    fuzz_type = get_fuzz_type_by_param_type(fuzzer_type)
                    sample_data = get_sample_data_by_type(param.get('type'))
                    # get parameter placement(in): path, query, header, cookie
                    # get parameter type: integer, string
                    # get format if present
                    param_type = param.get('in')
                    param_name = '{}|{}'.format(template_container_name, param.get('name'))
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
                        tmp_api_resource.update(self.get_schema(param))
                        template.data.append(fuzz_type(name=param_name, value=transform_data_to_bytes(sample_data)))
                    else:
                        self.logger.error('Can not parse a definition from swagger.json: %s', param)
                    if param.get('schema'):
                        tmp_api_resource.update(self.get_schema(param))
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

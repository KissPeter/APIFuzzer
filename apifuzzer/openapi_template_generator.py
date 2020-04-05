import json
from urllib.parse import urlparse

from apifuzzer.base_template import BaseTemplate
from apifuzzer.template_generator_base import TemplateGenerator
from apifuzzer.utils import get_sample_data_by_type, get_fuzz_type_by_param_type, transform_data_to_bytes, \
    get_api_definition_from_url, get_api_definition_from_file, get_item, pretty_print, set_class_logger, \
    get_base_url_form_api_src, FailedToParseFileException


class ParamTypes(object):
    PATH = 'path'
    QUERY = 'query'
    HEADER = 'header'
    COOKIE = 'cookie'
    BODY = 'body'
    FORM_DATA = 'formData'


class FailedToProcessSchemaException(Exception):
    pass


@set_class_logger
class OpenAPITemplateGenerator(TemplateGenerator):

    def __init__(self, api_resources, logger, api_definition_url):
        self.api_resources = api_resources
        self.templates = list()
        self.logger = logger
        self.logger.info('Logger initialized')
        self.api_definition_url = api_definition_url

    @staticmethod
    def normalize_url(url_in):
        # Kitty doesn't support some characters as template name so need to be cleaned, but it is necessary, so
        # we will change back later
        return url_in.strip('/').replace('/', '+')

    def get_properties_from_schema_definition(self, schema_def, schema_path=None):
        """
        :param schema_def: schema definition
        :type schema_def: dict
        :param schema_path: parameters path in schema
        :type schema_path: list, None
        """
        # handle case when heading string is /
        if isinstance(schema_path, str):
            _tmp_list = schema_path.split('/')
            schema_path = list()
            for item in _tmp_list:
                if len(item):
                    schema_path.append(item)
        # if reference is for a file, but no internal path:
        if len(schema_path):
            schema_path_extended = schema_path
            schema_path_extended.append('properties')
        else:
            schema_path_extended = ['properties']
        self.logger.debug('Getting {} from {}'.format(schema_path_extended, pretty_print(schema_def)))
        try:
            _return = get_item(schema_def, schema_path_extended)
        except KeyError as e:
            self.logger.debug('{} trying "parameters" key'.format(e))
            schema_path_extended.pop(len(schema_path_extended) - 1)
            schema_path_extended.append('parameters')
            _return = get_item(schema_def, schema_path_extended)
        self.logger.debug('Parameters found in schema: {}'.format(pretty_print(_return)))
        return _return

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
        Doc: https://swagger.io/docs/specification/using-ref/

        Local Reference
          - $ref: '#/definitions/myElement' # means go to the root of the current document and then find elements definitions and myElement one after one.

        Remote Reference
          - $ref: 'document.json' Uses the whole document located on the same server and in the same location.
          - The element of the document located on the same server – $ref: 'document.json#/myElement'
          - The element of the document located in the parent folder – $ref: '../document.json#/myElement'
          - The element of the document located in another folder – $ref: '../another-folder/document.json#/myElement'

        URL Reference
          - $ref: 'http://path/to/your/resource' Uses the whole document located on the different server.
          - The specific element of the document stored on the different server – $ref: 'http://path/to/your/resource.json#myElement'
          - The document on the different server, which uses the same protocol (for example, HTTP or HTTPS) – $ref: '//anotherserver.com/files/example.json'
        """
        schema_properties = None
        self.logger.info('Received schema definition: {}'.format(pretty_print(param)))
        schema_ref = param.get('schema', {}).get('$ref')
        if not schema_ref:
            raise FailedToProcessSchemaException('Faild to find shema ref in {}'.format(param))
        self.logger.debug('Processing param id {}, reference for schema: {}'.format(param.get('id'), schema_ref))
        # Local reference:
        # Example: $ref: '#/definitions/myElement'
        if schema_ref.startswith('#'):
            self.logger.debug('Looking for reference in local file: {}'.format(schema_ref))
            schema_path = schema_ref.split('/')
            # dropping first element of the list as it defines it is local reference (#)
            schema_path.pop(0)
            schema_definition = get_item(self.api_resources, schema_path)
            schema_properties = self.get_properties_from_schema_definition(schema_definition)
        # URL Reference
        # Example: $ref: 'http://path/to/your/resource.json#myElement''
        elif schema_ref.startswith('http'):
            self.logger.debug('Looking for remote reference: {}'.format(schema_ref))
            resource_reference, item_location = schema_ref.split('#', 1)
            self.logger.info('Downloading resource from: {} and using {}'.format(resource_reference, item_location))
            schema_definition = get_api_definition_from_url(resource_reference)
            schema_properties = self.get_properties_from_schema_definition(schema_definition, item_location)
        elif schema_ref.startswith('//'):
            self.logger.warning('Not implemented import: {}'.format(schema_ref))
            # The document on the different server, which uses the same protocol (for example, HTTP or HTTPS)
            # – $ref: '//anotherserver.com/files/example.json'
        # Remote (file) reference
        # Example: $ref: 'document.json#/myElement'
        else:
            file_reference, item_location = schema_ref.split('#', 1)
            self.logger.debug('It seems the schema is stored in local file {}, schema location: {}'
                              .format(file_reference, item_location))
            try:
                schema_definition = get_api_definition_from_file(file_reference)
            except FailedToParseFileException:
                # This part is necessary only because some of the API definitions doesn't follow the standard
                if len(self.api_definition_url):
                    self.logger.debug('Local file is not available, but API definition was defined as URL ({}).'
                                      'Trying to fetch {} from the same location'
                                      .format(self.api_definition_url, file_reference))
                    api_definition_url = "/".join([get_base_url_form_api_src(self.api_definition_url), file_reference])
                    self.logger.debug('Trying to fetch api definition from: {}'.format(api_definition_url))
                    schema_definition = get_api_definition_from_url(api_definition_url)
                else:
                    self.logger.warning('Local file reference was found in API definition, but file is not available')
                    schema_definition = dict()
            schema_properties = self.get_properties_from_schema_definition(schema_definition, item_location)
        self.logger.info('Parameter definition: {} discovered from {}'.format(schema_properties, param))
        return schema_properties

    @staticmethod
    def transform_schema_definition_to_swagger_param_definition(param, schema_def):
        _return = list()
        param_in = param.get('in')
        param_required = param.get('required')
        param_descr = param.get('description')
        for schema_def_key in schema_def.keys():
            _return.append(
                {'name': schema_def_key,
                 'in': param_in if param_in else schema_def[schema_def_key].get('in'),
                 'required': param_required if param_required else schema_def[schema_def_key].get('required'),
                 'type': schema_def[schema_def_key].get('type'),
                 'description': param_descr if param_descr else schema_def[schema_def_key].get('description')
                 }
            )
        return _return

    def process_schema(self, resource, method, param, tmp_api_resource):
        if not tmp_api_resource.get(resource, {}).get(method, {}).get('parameters'):
            tmp_api_resource[resource] = dict()
            tmp_api_resource[resource][method] = dict()
            tmp_api_resource[resource][method]['parameters'] = list()
        try:
            received_schema_def = self.get_schema(param)
            processed_schema = self.transform_schema_definition_to_swagger_param_definition(param, received_schema_def)
            tmp_api_resource[resource][method]['parameters'].extend(processed_schema)
        except FailedToProcessSchemaException as e:
            self.logger.warning(e)
        return tmp_api_resource

    def process_api_resources(self, paths=None):
        self.logger.info('Start preparation')
        tmp_api_resource = dict()
        if not paths:
            paths = self.api_resources['paths']
        else:
            self.logger.info('Processing extra parameter: {}'.format(pretty_print(paths)))
        for resource in paths.keys():
            normalized_url = self.normalize_url(resource)
            for method in paths[resource].keys():
                self.logger.info('Resource: {} Method: {}'.format(resource, method))
                template_container_name = '{}|{}'.format(normalized_url, method)
                template = BaseTemplate(name=template_container_name)
                template.url = normalized_url
                template.method = method.upper()
                for param in paths[resource][method].get('parameters', {}):
                    self.logger.info('Processing parameter: {}'.format(param))
                    if not isinstance(param, dict):
                        self.logger.warning('{} type mismatch, dict expected, got: {}'.format(param, type(param)))
                        param = json.loads(param)
                    if param.get('type'):
                        param_type = param.get('type')
                    elif param.get('schema', {}).get('type'):
                        param_type = param.get('schema', {}).get('type')
                    else:
                        param_type = 'string'
                    param_format = param.get('format')
                    if param_format is not None:
                        fuzzer_type = param_format.lower()
                    elif param_type is not None:
                        fuzzer_type = param_type.lower()
                    else:
                        fuzzer_type = None
                    fuzz_type = get_fuzz_type_by_param_type(fuzzer_type)
                    if param.get('example'):
                        sample_data = param.get('example')
                    elif param.get('schema', {}).get('example'):
                        sample_data = param.get('schema', {}).get('example')
                    else:
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
                    elif param_type == ParamTypes.BODY:
                        tmp_api_resource = self.process_schema(resource, method, param, tmp_api_resource)
                        # template.data.append(fuzz_type(name=param_name, value=transform_data_to_bytes(sample_data)))
                    elif param_type == ParamTypes.FORM_DATA:
                        template.params.append(fuzz_type(name=param_name, value=str(sample_data)))
                    elif len(param.get('$ref')):
                        self.logger.info('Only schema reference found in the parameter description: {}'.format(param))
                        tweaked_param = {'schema': param}
                        tmp_api_resource = self.process_schema(resource, method, tweaked_param, tmp_api_resource)
                    else:
                        self.logger.error('Can not parse a definition: %s', param)
                    if param.get('schema'):
                        tmp_api_resource = self.process_schema(resource, method, param, tmp_api_resource)
                self.templates.append(template)
        if len(tmp_api_resource):
            self.logger.info(
                'Additional resources were found, processing these: {}'.format(pretty_print(tmp_api_resource)))
            self.process_api_resources(paths=tmp_api_resource)

    def compile_base_url_for_swagger(self, alternate_url):
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

    def compile_base_url_for_openapi(self, alternate_url):
        uri = urlparse(self.api_resources.get('servers')[0].get('url'))
        if alternate_url:
            _base_url = "/".join([alternate_url.strip('/'), uri.path.strip('/')])
        else:
            _base_url = self.api_resources.get('servers')[0].get('url')
        return _base_url

    def compile_base_url(self, alternate_url):
        """
        :param alternate_url: alternate protocol and base url to be used instead of the one defined in swagger
        :type alternate_url: string
        """
        if self.api_resources.get('swagger', "").startswith('2'):
            _base_url = self.compile_base_url_for_swagger(alternate_url)
            self.logger.debug('Using swagger style url: {}'.format(_base_url))
        elif self.api_resources.get('openapi', "").startswith('3'):
            _base_url = self.compile_base_url_for_swagger(alternate_url)
            self.logger.debug('Using openapi style url: {}'.format(_base_url))
        else:
            self.logger.warning('Failed to find base url, using the alternative one ({})'.format(alternate_url))
            _base_url = alternate_url
        return _base_url

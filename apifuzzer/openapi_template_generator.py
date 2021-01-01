import json
from urllib.parse import urlparse

from apifuzzer.base_template import BaseTemplate
from apifuzzer.exceptions import FailedToProcessSchemaException
from apifuzzer.fuzz_utils import get_sample_data_by_type, get_api_definition_from_url, get_api_definition_from_file, \
    get_base_url_form_api_src, FailedToParseFileException, get_fuzz_type_by_param_type
from apifuzzer.template_generator_base import TemplateGenerator
from apifuzzer.utils import transform_data_to_bytes, get_item, pretty_print, get_logger


class ParamTypes(object):
    PATH = 'path'
    QUERY = 'query'
    HEADER = 'header'
    COOKIE = 'cookie'
    BODY = 'body'
    FORM_DATA = 'formData'


class OpenAPITemplateGenerator(TemplateGenerator):
    """
    This class processes the Swagger, OpenAPI v2 and OpenAPI v3 definitions. Generates Fuzz template from the params
    discovered.
    """

    def __init__(self, api_resources, api_definition_url):
        """
        :param api_resources: API resources in JSON format
        :type api_resources: dict
        :param api_definition_url: URL where the request should be sent
        :type api_definition_url: st
        """
        super().__init__()
        self.api_resources = api_resources
        self.templates = set()
        self.logger = get_logger(self.__class__.__name__)
        self.api_definition_url = api_definition_url

    @staticmethod
    def _normalize_url(url_in):
        """
        Kitty doesn't support some characters as template name so need to be cleaned, but it is necessary,
        so we will change back later
        :param url_in: url to process
        :type url_in: str
        :return: processed url
        :rtype: str
        """
        return url_in.strip('/').replace('/', '+')

    def get_properties_from_schema_definition(self, schema_def, schema_path=None):
        """
        Process section of a schema definition
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
        _return = dict()
        for key_to_look_for in ['properties', 'parameters', 'content']:
            # if reference is for a file, but no internal path:
            if schema_path and len(schema_path):
                schema_path_extended = schema_path
                schema_path_extended.append(key_to_look_for)
            else:
                schema_path_extended = [key_to_look_for]
            self.logger.debug('Getting {} from {}'.format(schema_path_extended, pretty_print(schema_def, 500)))
            try:
                _return = get_item(schema_def, schema_path_extended)
                if len(_return):
                    break
            except KeyError as e:
                self.logger.debug(f'{key_to_look_for} not found:{e}')
            # remove last bit -> key_to_look_for
            schema_path_extended.pop(len(schema_path_extended) - 1)
        self.logger.debug('Parameters found in schema: {}'.format(pretty_print(_return)))
        return _return

    def _add_extracted_references(self, resource, method, schema_definition):
        self.logger.debug(f'Add {pretty_print(schema_definition.get(resource, {}).get(method), 500)}')
        existing_param_names = set()
        if not self.api_resources['paths'][resource][method].get('parameters'):
            self.api_resources['paths'][resource][method]['parameters'] = list()
        for existing_param in self.api_resources['paths'][resource][method]['parameters']:
            existing_param_names.add(existing_param.get('name'))
        for schema_def in schema_definition.get(resource, {}).get(method, {}).get('parameters', []):
            if schema_def.get('name') not in existing_param_names:
                self.logger.debug(f'Update {resource}/{method} with definition {pretty_print(schema_def)}')
                self.api_resources['paths'][resource][method]['parameters'].append(schema_def)
        self.logger.debug(f'Updated definition: {pretty_print(schema_definition.get(resource, {}).get(method), 500)}')

    def resolve_json_reference(self, param):
        """
        Processes schema referenced if request method should be POST and request should contain body
        :type: param section of api definition

        Example:
            {
            "in": "body",
            "name": "body",
            "description": "Pet object that needs to be added to the store",
            "required": False,
            "schema": {
                    "$ref": "#/definitions/Pet"
                }
            }
        Doc: https://swagger.io/docs/specification/using-ref/
        Local Reference
            - $ref: '#/definitions/myElement' # means go to the root of the current document and then find elements
            definitions and myElement one after one.

        Remote Reference
             - $ref: 'document.json' Uses the whole document located on the same server and in the same location.
            - The element of the document located on the same server – $ref: 'document.json#/myElement'
            - The element of the document located in the parent folder – $ref: '../document.json#/myElement'
            - The element of the document located in another folder – $ref: '../another-folder/document.json#/myElement'

        URL Reference
            - $ref: 'http://path/to/your/resource' Uses the whole document located on the different server.
            - The specific element of the document stored on the different server:
             – $ref: 'http://path/to/your/resource.json#myElement'
            - The document on the different server, which uses the same protocol (for example, HTTP or HTTPS):
             – $ref: '//anotherserver.com/files/example.json'

        This is a bit messy now, but once https://github.com/jacksmith15/json-ref-dict/issues/14
        resolved this can be added:
        from jsonref import JsonRef
        ref = RefDict(file)
        resolved = materialize(ref)
        Alternative: OpenApiParser
        Open issue: https://gitlab.com/Hares-Lab/openapi-parser/-/issues/1
        """
        schema_properties = None
        self.logger.info('Received schema definition: {}'.format(pretty_print(param, limit=500)))
        schema_ref = param.get('schema', {}).get('$ref', '').strip()
        if not schema_ref:
            raise FailedToProcessSchemaException('Faild to find shema ref in {}'.format(param))
        self.logger.debug(f'Processing param id {param.get("id")}, reference for schema: {schema_ref}')
        # Local reference:
        # Example: $ref: '#/definitions/myElement'
        if schema_ref.startswith('#'):
            schema_path = schema_ref.split('/')
            # dropping first element of the list as it defines it is local reference (#)
            schema_path.pop(0)
            self.logger.debug(f'Looking for reference in local file: {schema_path}')
            schema_definition = get_item(self.api_resources, schema_path)
            schema_properties = self.get_properties_from_schema_definition(schema_definition)
        # URL Reference
        # Example: $ref: 'http://path/to/your/resource.json#myElement''
        elif schema_ref.startswith('http'):
            self.logger.debug('Looking for remote reference: {}'.format(schema_ref))
            resource_reference, item_location = schema_ref.split('#', 1)
            self.logger.info('Downloading resource from: {} and using {}'.format(resource_reference, item_location))
            schema_definition = get_api_definition_from_url(resource_reference, logger=self.logger.debug)
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
                schema_definition = get_api_definition_from_file(file_reference, logger=self.logger.debug)
            except FailedToParseFileException:
                # This part is necessary only because some of the API definitions doesn't follow the standard
                if len(self.api_definition_url):
                    self.logger.debug('Local file is not available, but API definition was defined as URL ({}).'
                                      'Trying to fetch {} from the same location'
                                      .format(self.api_definition_url, file_reference))
                    api_definition_url = "/".join([get_base_url_form_api_src(self.api_definition_url), file_reference])
                    self.logger.debug('Trying to fetch api definition from: {}'.format(api_definition_url))
                    schema_definition = get_api_definition_from_url(api_definition_url, logger=self.logger.debug)
                else:
                    self.logger.warning('Local file reference was found in API definition, but file is not available')
                    schema_definition = dict()
            schema_properties = self.get_properties_from_schema_definition(schema_definition, item_location)
        self.logger.debug('Parameter definition: {} discovered from {}'.format(schema_properties, param))
        return schema_properties

    def transform_schema_definition_key_to_swagger_param_definition(self, param, schema_def_key, schema_def_data):
        """
        Extracts parameters from a schema definition
        :param param: parameter of API resources
        :type param: dict
        :param schema_def_key: name of schema. Used only if not available in schema definition
        :type schema_def_key: str
        :param schema_def_data: schema definition to process
        :type schema_def_data: dict
        :return: extracted parameters
        :rtype: list of dicts
        """
        self.logger.debug('Processing schema param: {}'.format(schema_def_data))
        _return = list()
        param_in = param.get('in')
        param_required = param.get('required', True)
        schema_name = schema_def_data.get('name') if schema_def_data.get('name') else schema_def_key
        _schema_definition = {'name': schema_name,
                              'in': schema_def_data.get('in') if schema_def_data.get('in') else param_in,
                              'required': schema_def_data.get('required') if schema_def_data.get('required')
                              else param_required,
                              'type': schema_def_data.get('type', "string")
                              }
        # If the schema definition contains further parameters they are added to the extracted data
        if schema_def_data.get('schema'):
            self.logger.debug('Adding sample data ({}) to {}'
                              .format(schema_def_data.get('schema').items(), schema_def_key))
            for k, v in schema_def_data.get('schema').items():
                if not _schema_definition.get(k):
                    _schema_definition[k] = v
        # Another definition found, adding the reference. Further iteration is comming
        if schema_def_data.get('$ref'):
            _schema_definition['schema'] = {'$ref': schema_def_data.get('$ref')}
        self.logger.debug('Processed schema: {}'.format(pretty_print(_schema_definition)))
        _return.append(_schema_definition)
        return _return

    def transform_schema_definition_to_swagger_param_definition(self, param, schema_def):
        """
        Iterates through the schema definition and extract the parameters by calling the related function
        :param param: parameter of API resources
        :type param: dict
        :param schema_def: schema definition to process
        :type schema_def: dict
        :return: extracted parameters
        :rtype: list of dicts
        """
        _return = list()
        for schema_def_key in schema_def.keys():
            self.logger.debug('Processing schema definition: {}'.format(schema_def_key))
            _return.extend(self.transform_schema_definition_key_to_swagger_param_definition(
                param, schema_def_key, schema_def[schema_def_key]))
        return _return

    def process_schema(self, resource, method, param, tmp_api_resource):
        """
        First level of schema processing
        :param resource: API resource
        :type resource: str
        :param method: method of API resource
        :type method: str
        :param param: parameter of API resource we are processing. Some parts will be necessary
        :type param: dict
        :param tmp_api_resource: this is the place of resources to be extended
        :type tmp_api_resource: dict
        :return: tmp:api_resource
        :rtype dict
        """
        if not tmp_api_resource.get(resource, {}).get(method, {}).get('parameters'):
            tmp_api_resource[resource] = dict()
            tmp_api_resource[resource][method] = dict()
            tmp_api_resource[resource][method]['parameters'] = list()
        try:
            received_schema_def = self.resolve_json_reference(param)
            processed_schema = self.transform_schema_definition_to_swagger_param_definition(param, received_schema_def)
        except FailedToProcessSchemaException as e:
            self.logger.debug(f'{e}, trying to find details directly from parameter: {param}')
            processed_schema = self.transform_schema_definition_key_to_swagger_param_definition(param, '', param)
        self.logger.debug(f'Processes schema: {processed_schema}')
        tmp_api_resource[resource][method]['parameters'].extend(processed_schema)
        return tmp_api_resource

    def _get_template(self, template_name):
        """
        Starts new template if it does not exist yet or retrun the existing one which has the required name
        :param template_name: name of the template
        :type template_name: str
        :return: instance of BaseTemplate
        """
        _return = None
        for template in self.templates:
            self.logger.debug(f'Checking {template.name} vs {template_name}')
            if template.name == template_name:
                self.logger.debug(f'Loading existing template: {template.name}')
                _return = template
        if not _return:
            self.logger.debug(f'Open new Fuzz template for {template_name}')
            _return = BaseTemplate(name=template_name)
        return _return

    def _save_template(self, template):
        if template in self.templates:
            self.templates.remove(template)
        self.templates.add(template)
        self.logger.debug(f'Adding template to list: {template.name}, templates list: {len(self.templates)}')

    def pre_process_api_resources(self):
        """
        !!! Resolving references in OpenAPI definition isn't the best at the moment, once a reliable package will be
        available, this pat can be dropped and simplified !!!
        This code iterates through the API definition and tries to resolve the references. RequestBody not supported yet
        """
        iteration = 0
        while True:
            reference_resolved = False
            tmp_api_resource = dict()
            paths = self.api_resources['paths']
            for resource in paths.keys():
                for method in paths[resource].keys():
                    self.logger.debug(f'{iteration}. Resource: {resource} Method: {method}')
                    for param in paths[resource][method].get('parameters', []):
                        if param.get('schema'):
                            reference_resolved = True
                            tmp_api_resource = self.process_schema(resource, method, param, tmp_api_resource)
                            param.pop('schema')
                        if len(param.get("$ref", "")):
                            self.logger.debug(f'{iteration}. Only schema reference found in the parameter: {param}')
                            if param.get('schema'):
                                tweaked_param = {'schema': param}
                            else:
                                tweaked_param = param
                            self.logger.debug(f'{iteration}. Processing {tweaked_param}')
                            reference_resolved = True
                            tmp_api_resource = self.process_schema(resource, method, tweaked_param, tmp_api_resource)
                            param.pop('$ref')
                        else:
                            self.logger.debug(f'{iteration}. There is nothing to resolve: {param}')
                        if len(tmp_api_resource):
                            self._add_extracted_references(resource, method, tmp_api_resource)
            if not reference_resolved:
                break
            iteration += 1

    def process_api_resources(self, paths=None):
        self.logger.info('Start preparation')
        self.pre_process_api_resources()
        paths = self.api_resources['paths']
        for resource in paths.keys():
            normalized_url = self._normalize_url(resource)
            for method in paths[resource].keys():
                self.logger.info('Resource: {} Method: {}'.format(resource, method))
                template_name = '{}|{}'.format(normalized_url, method)
                template = self._get_template(template_name)
                template.url = normalized_url
                template.method = method.upper()
                for param in list(paths[resource][method].get('parameters', {})):
                    if not isinstance(param, dict):
                        self.logger.warning('{} type mismatch, dict expected, got: {}'.format(param, type(param)))
                        param = json.loads(param)

                    if param.get('type'):
                        parameter_data_type = param.get('type')
                    elif param.get('schema', {}).get('type'):
                        parameter_data_type = param.get('schema', {}).get('type')
                    else:
                        parameter_data_type = 'string'
                    param_format = param.get('format')

                    if param_format is not None:
                        fuzzer_type = param_format.lower()
                    elif parameter_data_type is not None:
                        fuzzer_type = parameter_data_type.lower()
                    else:
                        fuzzer_type = None
                    fuzz_type = get_fuzz_type_by_param_type(fuzzer_type)

                    if param.get('example'):
                        sample_data = param.get('example')
                    elif param.get('schema', {}).get('example'):
                        sample_data = param.get('schema', {}).get('example')
                    else:
                        sample_data = get_sample_data_by_type(param.get('type'))

                    parameter_place_in_request = param.get('in')
                    param_name = '{}|{}'.format(template_name, param.get('name'))

                    self.logger.info(f'Resource: {resource} Method: {method} Parameter: {param}, Parameter type: '
                                     f'{parameter_place_in_request}, Sample data: {sample_data}, Param name: '
                                     f'{param_name}, fuzzer: {fuzz_type.__name__}')

                    if parameter_place_in_request == ParamTypes.PATH:
                        template.path_variables.add(fuzz_type(name=param_name, value=str(sample_data)))
                    elif parameter_place_in_request == ParamTypes.HEADER:
                        template.headers.add(fuzz_type(name=param_name, value=transform_data_to_bytes(sample_data)))
                    elif parameter_place_in_request == ParamTypes.COOKIE:
                        template.cookies.add(fuzz_type(name=param_name, value=sample_data))
                    elif parameter_place_in_request == ParamTypes.QUERY:
                        template.params.add(fuzz_type(name=param_name, value=str(sample_data)))
                    elif parameter_place_in_request == ParamTypes.BODY:
                        template.data.add(fuzz_type(name=param_name, value=transform_data_to_bytes(sample_data)))
                    elif parameter_place_in_request == ParamTypes.FORM_DATA:
                        template.params.add(fuzz_type(name=param_name, value=str(sample_data)))
                    else:
                        self.logger.warning('Can not parse a definition: %s', param)
                self._save_template(template)

    def _compile_base_url_for_swagger(self, alternate_url):
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

    def _compile_base_url_for_openapi(self, alternate_url):
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
            _base_url = self._compile_base_url_for_swagger(alternate_url)
            self.logger.debug('Using swagger style url: {}'.format(_base_url))
        elif self.api_resources.get('openapi', "").startswith('3'):
            _base_url = self._compile_base_url_for_swagger(alternate_url)
            self.logger.debug('Using openapi style url: {}'.format(_base_url))
        else:
            self.logger.warning('Failed to find base url, using the alternative one ({})'.format(alternate_url))
            _base_url = alternate_url
        return _base_url

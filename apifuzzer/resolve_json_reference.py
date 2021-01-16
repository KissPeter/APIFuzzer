import os.path
from copy import deepcopy

from jsonpath_ng import parse

from apifuzzer.fuzz_utils import get_api_definition_from_url, get_base_url_form_api_src, FailedToParseFileException, \
    get_api_definition_from_file
from apifuzzer.utils import pretty_print, get_logger


class FailedToResolveReference(Exception):
    pass


class ResolveReferences:

    def __init__(self, api_definition_path=None, api_definition_url=""):
        self.logger = get_logger(self.__class__.__name__)
        self.api_definition = self._get_api_definition(api_definition_path, api_definition_url)
        self.api_definition_path = api_definition_path
        self.api_definition_base_path = self._get_base_path_of_file(api_definition_path)
        self.api_definition_url = api_definition_url
        self.additional_api_definition = deepcopy(self.api_definition)

    def _get_api_definition(self, path, url):
        if path is not None:
            return get_api_definition_from_file(path, logger=self.logger.debug)
        elif url is not None:
            return get_api_definition_from_url(url, logger=self.logger.debug)

    def _get_base_path_of_file(self, path):
        if path:
            return os.path.abspath(os.path.join(path, os.pardir))
        else:
            self.logger.warning(f'Failed to get directory for file path')
            return '.'

    def _find_by_jsonpath(self, data, path):
        search_path = list()
        for part in path.split('/')[1:]:
            search_path.append(str(part))
        search_path_str = ".".join(search_path)
        self.logger.debug(f'Search {search_path_str} in json: {pretty_print(data)}')
        try:
            jsonpath_expression = parse(search_path_str)
            matches = jsonpath_expression.find(data)
        except Exception as e:
            self.logger.warning(f'Failed to find {search_path_str} because: {e}')
            matches = list()
        if len(matches):
            self.logger.debug(f'Json data {path} match: {matches[0].value}')
            return matches[0].value
        else:
            self.logger.warning(f'No {path} in {pretty_print(data)}')
            return None

    def _resolve_json_reference(self, schema_path, schema_ref):
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
        resource_reference, item_location = schema_ref.split('#', 1)

        schema_definition = dict()
        # Local reference:
        # Example: $ref: '#/definitions/myElement'
        if schema_ref.startswith('#'):
            self.logger.debug(f'Looking for reference in local file: {schema_path}')
        # URL Reference
        # Example: $ref: 'http://path/to/your/resource.json#myElement''
        elif schema_ref.startswith('http'):
            self.logger.info('Downloading resource from: {} and using {}'.format(resource_reference, item_location))
            self.additional_api_definition.update(
                get_api_definition_from_url(resource_reference, logger=self.logger.debug))
        elif schema_ref.startswith('//'):
            self.logger.warning('Not implemented import: {}'.format(schema_ref))
            # The document on the different server, which uses the same protocol (for example, HTTP or HTTPS)
            # – $ref: '//anotherserver.com/files/example.json'
        # Remote (file) reference
        # Example: $ref: 'document.json#/myElement'
        elif len(schema_ref):
            self.logger.debug(f'Received reference: {schema_ref}')
            self.logger.debug('It seems the schema is stored in local file {}, schema location: {}'
                              .format(resource_reference, item_location))
            try:
                filepath = os.path.join(self.api_definition_base_path, resource_reference)
                self.additional_api_definition.update(get_api_definition_from_file(filepath, logger=self.logger.debug))
            except FailedToParseFileException:
                # This part is necessary only because some of the API definitions doesn't follow the standard
                if len(self.api_definition_url):
                    self.logger.debug('Local file is not available, but API definition was defined as URL ({}).'
                                      'Trying to fetch {} from the same location'
                                      .format(self.api_definition_url, resource_reference))
                    api_definition_url = "/".join(
                        [get_base_url_form_api_src(self.api_definition_url), resource_reference])
                    self.logger.debug('Trying to fetch api definition from: {}'.format(api_definition_url))
                    self.additional_api_definition.update(
                        get_api_definition_from_url(api_definition_url, logger=self.logger.debug))
                else:
                    msg = 'Local file reference was found in API definition, but file is not available'
                    self.logger.error(msg)
                    raise FailedToResolveReference(msg)

        else:
            self.logger.debug(f'Nothing to extract: {schema_path} - {schema_ref}')
        schema_definition_filtered = self._find_by_jsonpath(self.additional_api_definition, item_location)
        self.logger.debug(
            f'Parameter definition: {pretty_print(schema_definition_filtered, 50)} discovered from {schema_ref}')
        return schema_definition_filtered

    def _resolve(self, data):
        ref_found = False
        self.logger.debug(f'Processing {pretty_print(data, 50)}')
        if isinstance(data, dict):
            return_data = dict()
            for key, value in data.items():
                self.logger.debug(f'Checking {key} - {pretty_print(value, 50)}')
                if isinstance(value, dict):
                    self.logger.debug(f'Process dict {key}')
                    return_data[key] = self.resolve(value)
                elif isinstance(value, list):
                    if not return_data.get(key):
                        return_data[key] = list()
                    for iter in range(len(value)):
                        self.logger.debug(f'Process {key} list elem: {iter}')
                        return_data[key].append(self.resolve(data=data[key][iter]))
                elif key == '$ref' and value:
                    ref_found = True
                    try:
                        return_data = self._resolve_json_reference(schema_path=key, schema_ref=value)
                        self.logger.debug(f'Processed {key} -> {pretty_print(return_data)}')
                    except FailedToResolveReference:
                        return_data = None
                else:
                    return_data[key] = value
                    if isinstance(value, str) and '$ref' in value:
                        ref_found = True
                        self.logger.warning(f'Unresolved reference:{key} -  {type(value)} {pretty_print(value)}')
                self.logger.debug(f'Processed: {key}')

        else:
            return_data = data
            if not isinstance(data, str):
                self.logger.warning(f'2 Nothing to do with {type(data)}: {data}')
        return [return_data, ref_found]

    def resolve(self, data=None):
        self.logger.info('Resolving API internal references, may take a while')
        if data is None:
            data = self.api_definition
        resolved_in_this_iteration = True

        iteration = 1
        while resolved_in_this_iteration:
            self.logger.debug(f'{iteration} resolving reference')
            data, resolved_in_this_iteration = self._resolve(data)
            iteration += 1
        return data

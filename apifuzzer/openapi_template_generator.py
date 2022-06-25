import json
from urllib.parse import urlparse

from json_ref_dict import materialize, RefDict

from apifuzzer.base_template import BaseTemplate
from apifuzzer.fuzz_utils import _get_sample_data_by_type, get_fuzz_type_by_param_type
from apifuzzer.move_json_parts import JsonSectionAbove
from apifuzzer.template_generator_base import TemplateGenerator
from apifuzzer.utils import transform_data_to_bytes, pretty_print, get_logger


class ParamTypes(object):
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"
    FORM_DATA = "formData"


class OpenAPITemplateGenerator(TemplateGenerator):
    """
    This class processes the Swagger, OpenAPI v2 and OpenAPI v3 definitions. Generates Fuzz template from the params
    discovered.
    """

    def __init__(self, api_definition_url, api_definition_file):
        """
        :param api_definition_file: API resources local file
        :type api_definition_file: str
        :param api_definition_url: URL where the request should be sent
        :type api_definition_url: str
        """
        super().__init__()
        self.templates = set()
        self.logger = get_logger(self.__class__.__name__)
        self.api_definition_url = api_definition_url
        self.api_definition_file = api_definition_file
        tmp_api_resources = self.resolve_json_references()
        self.json_formatter = JsonSectionAbove(tmp_api_resources)
        self.api_resources = self.json_formatter.resolve()

    def resolve_json_references(self):
        if self.api_definition_url:
            reference = self.api_definition_url
        else:
            reference = self.api_definition_file
        ref = RefDict(reference)
        return materialize(ref)

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
        return url_in.strip("/").replace("/", "+")

    def _get_template(self, template_name):
        """
        Starts new template if it does not exist yet or retrun the existing one which has the required name
        :param template_name: name of the template
        :type template_name: str
        :return: instance of BaseTemplate
        """
        _return = None
        for template in self.templates:
            self.logger.debug(f"Checking {template.name} vs {template_name}")
            if template.name == template_name:
                self.logger.debug(f"Loading existing template: {template.name}")
                _return = template
        if not _return:
            self.logger.debug(f"Open new Fuzz template for {template_name}")
            _return = BaseTemplate(name=template_name)
        return _return

    def _save_template(self, template):
        if template in self.templates:
            self.logger.debug(f"Removing previous version of {template.name}")
            self.templates.remove(template)
        self.templates.add(template)
        self.logger.debug(
            f"Adding template to list: {template.name}, templates list: {len(self.templates)}"
        )

    @staticmethod
    def _split_content_type(content_type):
        """
        application/x-www-form-urlencoded -> x-www-form-urlencoded
        multipart/form-data               -> form-data
         application/json                 -> json
        :param content_type:
        :return:
        """
        if "/" in content_type:
            return content_type.split("/", 1)[1]
        else:
            return content_type

    def process_api_resources(
        self, paths=None, existing_template=None
    ):  # pylint: disable=W0221
        self.logger.info("Start preparation")
        self._process_request_body()
        self._process_api_resources()

    def _process_request_body(self):
        paths = self.api_resources["paths"]
        request_body_paths = dict()
        for resource in paths.keys():
            normalized_url = self._normalize_url(resource)
            if not request_body_paths.get(resource):
                request_body_paths[resource] = dict()
            for method in paths[resource].keys():
                if not request_body_paths[resource].get(method):
                    request_body_paths[resource][method] = dict()
                for content_type in (
                    paths[resource][method].get("requestBody", {}).get("content", [])
                ):
                    # as multiple content types can exist here, we need to open up new template
                    template_name = f"{normalized_url}|{method}-{self._split_content_type(content_type)}"
                    self.logger.info(
                        f"Resource: {resource} Method: {method}, CT: {content_type}"
                    )
                    template = self._get_template(template_name)
                    template.url = normalized_url
                    template.method = method.upper()
                    template.content_type = content_type
                    if not request_body_paths[resource][method].get("parameters"):
                        request_body_paths[resource][method]["parameters"] = []
                    for k, v in paths[resource][method]["requestBody"]["content"][
                        content_type
                    ].items():
                        request_body_paths[resource][method]["parameters"].append(
                            {"in": "body", k: v}
                        )
                    self._process_api_resources(
                        paths=request_body_paths, existing_template=template
                    )

    def _process_api_resources(self, paths=None, existing_template=None):
        if paths is None:
            paths = self.api_resources.get("paths")
        for resource in paths.keys():
            normalized_url = self._normalize_url(resource)
            for method in paths[resource].keys():
                self.logger.info("Resource: {} Method: {}".format(resource, method))
                if existing_template:
                    template = existing_template
                    template_name = existing_template.name
                else:
                    template_name = "{}|{}".format(normalized_url, method)
                    template = self._get_template(template_name)
                template.url = normalized_url
                template.method = method.upper()
                # Version 2: Set content type (POST, PUT method)
                if len(paths[resource][method].get("consumes", [])):
                    template.content_type = paths[resource][method]["consumes"][0]

                for param in list(paths[resource][method].get("parameters", {})):
                    if not isinstance(param, dict):
                        self.logger.warning(
                            "{} type mismatch, dict expected, got: {}".format(
                                param, type(param)
                            )
                        )
                        param = json.loads(param)

                    if param.get("type"):
                        parameter_data_type = param.get("type")
                    else:
                        parameter_data_type = "string"
                    param_format = param.get("format")

                    if param.get("example"):
                        sample_data = param.get("example")
                    elif param.get("default"):
                        sample_data = param.get("default")
                    else:
                        sample_data = _get_sample_data_by_type(param.get("type"))

                    parameter_place_in_request = param.get("in")
                    parameters = list()
                    if param.get("name"):
                        param_name = f'{template_name}|{param.get("name")}'
                        parameters.append(
                            {"name": param_name, "type": parameter_data_type}
                        )
                    for _param in param.get("properties", []):
                        param_name = f"{template_name}|{_param}"
                        parameter_data_type = (
                            param.get("properties", {})
                                .get(_param)
                                .get("type", "string")
                        )
                        self.logger.debug(
                            f"Adding property: {param_name} with type: {parameter_data_type}"
                        )
                        parameters.append(self._get_additional_parameters(_param, param, param_name,
                                                                          parameter_data_type))
                    for _parameter in parameters:
                        param_name = _parameter.get("name")
                        parameter_data_type = _parameter.get("type")
                        fuzzer_type = self._get_fuzzer_type(_parameter, param_format, parameter_data_type)
                        fuzz_type = get_fuzz_type_by_param_type(fuzzer_type)
                        sample_data = self._get_sample_data(_parameter, fuzz_type, sample_data)

                        self.logger.info(
                            f"Resource: {resource} Method: {method} \n Parameter: {param} \n"
                            f" Parameter place: {parameter_place_in_request} \n Sample data: {sample_data}"
                            f"\n Param name: {param_name}\n fuzzer_type: {fuzzer_type} "
                            f"fuzzer: {fuzz_type.__name__}"
                        )

                        self._add_field_to_param(fuzz_type, param, param_name, parameter_place_in_request, sample_data,
                                                 template)
                if template.get_stat() > 0:
                    self._save_template(template)

    @staticmethod
    def _get_additional_parameters(_param, param, param_name, parameter_data_type):
        _additional_param = {
            "name": param_name,
            "type": parameter_data_type,
            "default": param.get("properties", {})
                .get(_param)
                .get("default"),
            "example": param.get("properties", {})
                .get(_param)
                .get("example"),
            "enum": param.get("properties", {}).get(_param).get("enum"),
        }
        return _additional_param

    def _add_field_to_param(self, fuzz_type, param, param_name, parameter_place_in_request, sample_data, template):
        if parameter_place_in_request == ParamTypes.PATH:
            template.path_variables.add(
                fuzz_type(name=param_name, value=str(sample_data))
            )
        elif parameter_place_in_request == ParamTypes.HEADER:
            template.headers.add(
                fuzz_type(
                    name=param_name,
                    value=transform_data_to_bytes(sample_data),
                )
            )
        elif parameter_place_in_request == ParamTypes.COOKIE:
            template.cookies.add(
                fuzz_type(name=param_name, value=sample_data)
            )
        elif parameter_place_in_request == ParamTypes.QUERY:
            template.params.add(
                fuzz_type(name=param_name, value=str(sample_data))
            )
        elif parameter_place_in_request == ParamTypes.BODY:
            if hasattr(fuzz_type, "accept_list_as_value"):
                template.data.add(
                    fuzz_type(name=param_name, value=sample_data)
                )
            else:
                template.data.add(
                    fuzz_type(
                        name=param_name,
                        value=transform_data_to_bytes(sample_data),
                    )
                )
        elif parameter_place_in_request == ParamTypes.FORM_DATA:
            template.params.add(
                fuzz_type(name=param_name, value=str(sample_data))
            )
        else:
            self.logger.warning(
                f"Can not parse a definition ({parameter_place_in_request}): "
                f"{pretty_print(param)}"
            )

    @staticmethod
    def _get_sample_data(_parameter, fuzz_type, sample_data):
        if _parameter.get("enum") and hasattr(
            fuzz_type, "accept_list_as_value"
        ):
            sample_data = _parameter.get("enum")
        elif _parameter.get("example"):
            sample_data = _parameter.get("example")
        elif _parameter.get("default"):
            sample_data = _parameter.get("default")
        return sample_data

    @staticmethod
    def _get_fuzzer_type(_parameter, param_format, parameter_data_type):
        if _parameter.get("enum"):
            fuzzer_type = "enum"
        elif param_format is not None:
            fuzzer_type = param_format.lower()
        elif parameter_data_type is not None:
            fuzzer_type = parameter_data_type.lower()
        else:
            fuzzer_type = None
        return fuzzer_type

    def _compile_base_url_for_swagger(self, alternate_url):
        if alternate_url:
            _base_url = "/".join(
                [
                    alternate_url.strip("/"),
                    self.api_resources.get("basePath", "").strip("/"),
                ]
            )
        else:
            if "http" in self.api_resources["schemes"]:
                _protocol = "http"
            else:
                _protocol = self.api_resources["schemes"][0]
            _base_url = "{}://{}{}".format(
                _protocol, self.api_resources["host"], self.api_resources["basePath"]
            )
        return _base_url

    def _compile_base_url_for_openapi(self, alternate_url):
        if len(self.api_resources.get("servers", [])) > 0:
            uri = urlparse(self.api_resources.get("servers", [{}])[0].get("url"))
        else:
            uri = urlparse(alternate_url)
        if alternate_url:
            _base_url = "/".join([alternate_url.strip("/"), uri.path.strip("/")])
        else:
            _base_url = self.api_resources.get("servers", [{}])[0].get("url")
        return _base_url

    def compile_base_url(self, alternate_url):
        """
        :param alternate_url: alternate protocol and base url to be used instead of the one defined in swagger
        :type alternate_url: string
        """
        if self.api_resources.get("swagger", "").startswith("2"):
            _base_url = self._compile_base_url_for_swagger(alternate_url)
            self.logger.debug("Using swagger style url: {}".format(_base_url))
        elif self.api_resources.get("openapi", "").startswith("3"):
            _base_url = self._compile_base_url_for_openapi(alternate_url)
            self.logger.debug("Using openapi style url: {}".format(_base_url))
        else:
            self.logger.warning(
                "Failed to find base url, using the alternative one ({})".format(
                    alternate_url
                )
            )
            _base_url = alternate_url
        return _base_url

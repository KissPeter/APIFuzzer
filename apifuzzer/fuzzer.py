from kitty.interfaces import WebInterface
from kitty.model import GraphModel

from apifuzzer.fuzzer_target.fuzz_request_sender import FuzzerTarget
from apifuzzer.openapi_template_generator import OpenAPITemplateGenerator
from apifuzzer.server_fuzzer import OpenApiServerFuzzer
from apifuzzer.utils import set_logger
from apifuzzer.version import get_version


class Fuzzer(object):

    def __init__(self, api_resources, report_dir, test_level, log_level, basic_output, alternate_url=None,
                 test_result_dst=None,
                 auth_headers=None,
                 api_definition_url=None,
                 junit_report_path=None):
        self.api_resources = api_resources
        self.base_url = None
        self.alternate_url = alternate_url
        self.templates = None
        self.test_level = test_level
        self.report_dir = report_dir
        self.test_result_dst = test_result_dst
        self.auth_headers = auth_headers if auth_headers else {}
        self.junit_report_path = junit_report_path
        self.logger = set_logger(log_level, basic_output)
        self.logger.info('%s initialized', get_version())
        self.api_definition_url = api_definition_url

    def prepare(self):
        # here we will be able to branch the template generator if we will support other than Swagger / OpenAPI
        template_generator = OpenAPITemplateGenerator(self.api_resources, self.api_definition_url)
        template_generator.process_api_resources()
        self.templates = template_generator.templates
        self.base_url = template_generator.compile_base_url(self.alternate_url)

    def run(self):
        target = FuzzerTarget(name='target', base_url=self.base_url, report_dir=self.report_dir,
                              auth_headers=self.auth_headers, junit_report_path=self.junit_report_path)
        interface = WebInterface()
        model = GraphModel()
        for template in self.templates:
            model.connect(template.compile_template())
        fuzzer = OpenApiServerFuzzer()
        fuzzer.set_model(model)
        fuzzer.set_target(target)
        fuzzer.set_interface(interface)
        fuzzer.start()
        fuzzer.stop()

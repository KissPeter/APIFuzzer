import pycurl
import requests
import junit_xml
from apifuzzer.fuzz_utils import container_name_to_param
from apifuzzer.utils import get_logger
from apifuzzer.version import get_version


class JunitReport:
    def __init__(self, junit_report_path):
        self.junit_report_path = junit_report_path
        self.generate_junit_xml = len(junit_report_path)
        self.logger = get_logger(self.__class__.__name__)
        self.test_cases = list()


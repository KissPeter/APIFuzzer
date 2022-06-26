from time import time, perf_counter

import junit_xml

from apifuzzer.utils import get_logger


class JunitReport:
    def __init__(self, junit_report_path):
        self.junit_report_path = junit_report_path
        self.generate_junit_xml = len(junit_report_path)
        self.test_cases = list()
        self.test_case = None

    def add_testcase(self, test_number, test_report, start_transmit):
        self.test_case = junit_xml.TestCase(name=test_number, status=test_report.get_status(), timestamp=time(),
                                            elapsed_sec=perf_counter() - start_transmit)

    def save_testcase(self):
        self.test_cases.append(self.test_case)

    def save_report(self):
        if self.generate_junit_xml:
            with open(self.junit_report_path, "w") as report_file:
                junit_xml.to_xml_report_file(report_file,
                                             [junit_xml.TestSuite(name="API Fuzzer", test_cases=self.test_cases,
                                                                  timestamp=time())],
                                             prettyprint=True)

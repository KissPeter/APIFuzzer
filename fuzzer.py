#!/usr/bin/env python3
#  -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import argparse
import json
if sys.version_info[:2] == (2, 7):
    from logging import _levelNames as levelNames
else:
    from logging import _nameToLevel as levelNames
import signal
import tempfile


from kitty.interfaces import WebInterface
from kitty.model import GraphModel

from apifuzzer.swagger_template_generator import SwaggerTemplateGenerator
from apifuzzer.fuzzer_target import FuzzerTarget
from apifuzzer.server_fuzzer import OpenApiServerFuzzer
from apifuzzer.utils import set_logger


class Fuzzer(object):

    def __init__(self, api_resources, report_dir, test_level, log_level, alternate_url=None, test_result_dst=None):
        self.api_resources = api_resources
        self.base_url = None
        self.alternate_url = alternate_url
        self.templates = None
        self.test_level = test_level
        self.report_dir = report_dir
        self.test_result_dst = test_result_dst
        self.logger = set_logger(log_level)
        self.logger.info('APIFuzzer initialized')

    def prepare(self):
        # here we will be able to branch the template generator if we would like to support other than Swagger
        template_generator = SwaggerTemplateGenerator(self.api_resources)
        template_generator.process_api_resources()
        self.templates = template_generator.templates
        self.base_url = template_generator.compile_base_url(self.alternate_url)

    def run(self):
        target = FuzzerTarget(name='target', base_url=self.base_url, report_dir=self.report_dir)
        interface = WebInterface()
        model = GraphModel()
        for template in self.templates:
            model.connect(template.compile_template())
        fuzzer = OpenApiServerFuzzer()
        fuzzer.set_model(model)
        fuzzer.set_target(target)
        fuzzer.set_interface(interface)
        fuzzer.start()


if __name__ == '__main__':

    def signal_handler(**kwargs):
        sys.exit(0)

    parser = argparse.ArgumentParser(description='API fuzzer configuration',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=20))
    parser.add_argument('-s', '--src_file',
                        type=str,
                        required=True,
                        help='API definition file path',
                        dest='src_file')
    parser.add_argument('-r', '--report_dir',
                        type=str,
                        required=False,
                        help='Directory where error reports will be saved. Default is temporally generated directory',
                        dest='report_dir',
                        default=tempfile.mkdtemp())
    parser.add_argument('--level',
                        type=int,
                        required=False,
                        help='Test deepness: [1,2], higher is the deeper !!!Not implemented!!!',
                        dest='level',
                        default=1)
    parser.add_argument('-u', '--url',
                        type=str,
                        required=False,
                        help='Use CLI defined url instead compile the url from the API definition. Useful for testing',
                        dest='alternate_url',
                        default=None)
    parser.add_argument('-t', '--test_report',
                        type=str,
                        required=False,
                        help='JUnit test result xml save path !!!Not implemented!!!',
                        dest='test_result_dst',
                        default=None)
    parser.add_argument('--log',
                        type=str,
                        required=False,
                        help='Use different log level than the default WARNING',
                        dest='log_level',
                        default='warning',
                        choices=[level.lower() for level in levelNames if isinstance(level, str)])
    args = parser.parse_args()
    api_definition_json = dict()
    try:
        with open(args.src_file, 'r') as f:
            api_definition_json = json.loads(f.read())
    except Exception as e:
        print('Failed to parse input file: {}'.format(e))
        exit()
    prog = Fuzzer(api_resources=api_definition_json,
                  report_dir=args.report_dir,
                  test_level=args.level,
                  alternate_url=args.alternate_url,
                  test_result_dst=args.test_result_dst,
                  log_level=args.log_level
                  )
    prog.prepare()
    signal.signal(signal.SIGINT, signal_handler)
    prog.run()

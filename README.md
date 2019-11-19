[![Join the chat at https://gitter.im/API-Fuzzer/Lobby](https://badges.gitter.im/API-Fuzzer/Lobby.svg)](https://gitter.im/API-Fuzzer/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/eab6434d9bd742e3880d8f589a9cc0a6)](https://www.codacy.com/app/KissPeter/APIFuzzer?utm_source=github.com&utm_medium=referral&utm_content=KissPeter/APIFuzzer&utm_campaign=badger)
[![Maintainability](https://api.codeclimate.com/v1/badges/bfc9bda00deb5002b665/maintainability)](https://codeclimate.com/github/KissPeter/APIFuzzer/maintainability)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/KissPeter/APIFuzzer/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/KissPeter/APIFuzzer/?branch=master)
[![Build Status](https://travis-ci.org/KissPeter/APIFuzzer.svg?branch=master)](https://travis-ci.org/KissPeter/APIFuzzer)
[![Documentation Status](https://readthedocs.org/projects/apifuzzer/badge/?version=latest)](https://apifuzzer.readthedocs.io/)

# APIFuzzer — HTTP API Testing Framework


APIFuzzer reads your API description and step by step fuzzes the fields to validate 
if you application can cope with the fuzzed parameters. Does not require coding.

### Supported API Description Formats

- [Swagger][]

### Work in progress
- [API Blueprint][]

## Installation

Fetch the most recent code from GitHub
```
$ git clone https://github.com/KissPeter/APIFuzzer.git
```
Install requirements. If you don't have pip installed, then sudo apt-get install python3-pip -y 
```
$ pip3 install -r APIFuzzer/requirements.txt
```

## Quick Start
Check the help (some of them are not implemented yet):
```
$$ python3 fuzzer.py -h
usage: fuzzer.py [-h] -s SRC_FILE [-r REPORT_DIR] [--level LEVEL]
                 [-u ALTERNATE_URL] [-t TEST_RESULT_DST]
                 [--log {critical,fatal,error,warn,warning,info,debug,notset}]
                 [--headers HEADERS]

API fuzzer configuration

optional arguments:
  -h, --help        show this help message and exit
  -s SRC_FILE, --src_file SRC_FILE
                    API definition file path
  -r REPORT_DIR, --report_dir REPORT_DIR
                    Directory where error reports will be saved. Default is
                    temporally generated directory
  --level LEVEL     Test deepness: [1,2], higher is the deeper !!!Not
                    implemented!!!
  -u ALTERNATE_URL, --url ALTERNATE_URL
                    Use CLI defined url instead compile the url from the API
                    definition. Useful for testing
  -t TEST_RESULT_DST, --test_report TEST_RESULT_DST
                    JUnit test result xml save path !!!Not implemented!!!
  --log {critical,fatal,error,warn,warning,info,debug,notset}
                    Use different log level than the default WARNING
  --headers HEADERS
                    Http request headers added to all request. Example:
                    '[{"Authorization": "SuperSecret"}, {"Auth2": "asd"}]'

```

Usage example:

```
Start the sample application (install the necessary packages listed in test/requirements_for_test.txt):
$ python3 -m test.test_application

Start the fuzzer:
$ python3 fuzzer.py -s test/test_swagger_definition.json -u http://127.0.0.1:5000/ -r /tmp/reports/ --log debug 

Check the reports:
$ ls -1 /tmp/reports/

Report example:
$ json_pp < /tmp/reports/79_1573993485.5391517.json
{
   "response" : "Test application exception: invalid literal for int() with base 10: '0\\x00\\x10'",
   "sub_reports" : [],
   "parsed_status_code" : 500,
   "state" : "COMPLETED",
   "test_number" : 79,
   "request_body" : null,
   "reason" : "failed",
   "name" : "target",
   "request_url" : "http://127.0.0.1:5000/exception/0\u0000\u0010",
   "request_method" : "GET",
   "status" : "failed",
   "request_headers" : "{\"User-Agent\": \"APIFuzzer\", \"Accept-Encoding\": \"gzip, deflate\", \"Accept\": \"*/*\", \"Connection\": \"keep-alive\"}"
}
```

[API Blueprint]: https://apiblueprint.org/
[Swagger]: http://swagger.io/

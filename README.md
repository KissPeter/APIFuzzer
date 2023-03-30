[![Join the chat at https://gitter.im/API-Fuzzer/Lobby](https://badges.gitter.im/API-Fuzzer/Lobby.svg)](https://gitter.im/API-Fuzzer/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Test Coverage](https://api.codeclimate.com/v1/badges/bfc9bda00deb5002b665/test_coverage)](https://codeclimate.com/github/KissPeter/APIFuzzer/test_coverage)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/eab6434d9bd742e3880d8f589a9cc0a6)](https://www.codacy.com/app/KissPeter/APIFuzzer?utm_source=github.com&utm_medium=referral&utm_content=KissPeter/APIFuzzer&utm_campaign=badger)
[![Maintainability](https://api.codeclimate.com/v1/badges/bfc9bda00deb5002b665/maintainability)](https://codeclimate.com/github/KissPeter/APIFuzzer/maintainability)
[![Pypi downloads](https://img.shields.io/pypi/dw/APIFuzzer)](https://pypistats.org/packages/apifuzzer)
[![CI](https://github.com/KissPeter/APIFuzzer/actions/workflows/python-app.yml/badge.svg)](https://github.com/KissPeter/APIFuzzer/actions)

# APIFuzzer — HTTP API Testing Framework

APIFuzzer reads your API description and step by step fuzzes the fields to validate 
if you application can cope with the fuzzed parameters. Does not require coding.

## APIFuzzer main features

* Parse API definition from local file or remote URL
* JSON and YAML file format support
* All HTTP methods are supported
* Fuzzing of request body, query string, path parameter and request header are supported
* Relies on random mutations
* Support CI integration 
    * Generate JUnit XML test report format
    * Send request to alternative URL
    * Support HTTP basic auth from configuration
    * Save report of failed test in JSON format into the pre-configured folder
    * Log to stdout instead of syslog
* Configurable log level

### Supported API definition formats
- [Swagger][]
- [OpenAPI][]

### Planned
- [GraphQL][]
- [API Blueprint][]

## Installation

### With PIP

#### Pre-requirements
1. Python3
2. sudo apt install libcurl4-openssl-dev libssl-dev libcurl4-nss-dev (on Ubuntu 18.04, required by pycurl)
3. sudo apt install gcc libcurl4-nss-dev (on Ubuntu 20.04, required by pycurl)

Latest version:

```shell
pip3 install APIFuzzer
```
Development version: 
Fetch the most recent code from GitHub
```shell
$ git clone https://github.com/KissPeter/APIFuzzer.git
```
Install requirements. If you don't have pip installed, then sudo apt-get install python3-pip -y 
```shell
$ pip3 install -r APIFuzzer/requirements.txt
```

### Using Docker

```shell
$ docker pull kisspeter/apifuzzer:latest
```

## Quick Start
Check the help (some of them are not implemented yet):
```

$$ usage: APIFuzzer [-h] [-s SRC_FILE] [--src_url SRC_URL] [-r REPORT_DIR] [--level LEVEL] [-u ALTERNATE_URL] [-t TEST_RESULT_DST]
                 [--log {critical,fatal,error,warn,warning,info,debug,notset}] [--basic_output BASIC_OUTPUT] [--headers HEADERS] [-v ,--version]

APIFuzzer configuration

optional arguments:
  -h, --help            show this help message and exit
  -s SRC_FILE, --src_file SRC_FILE
                        API definition file path. JSON and YAML format is supported
  --src_url SRC_URL     API definition url. JSON and YAML format is supported
  -r REPORT_DIR, --report_dir REPORT_DIR
                        Directory where error reports will be saved. Default is temporally generated directory
  --level LEVEL         Test deepness: [1,2], the higher is the deeper (In progress)
  -u ALTERNATE_URL, --url ALTERNATE_URL
                        Use CLI defined url instead compile the url from the API definition. Useful for testing
  -t TEST_RESULT_DST, --test_report TEST_RESULT_DST
                        JUnit test result xml save path
  --log {critical,fatal,error,warn,warning,info,debug,notset}
                        Use different log level than the default WARNING
  --basic_output BASIC_OUTPUT
                        Use basic output for logging (useful if running in jenkins). Example --basic_output=True
  --headers HEADERS     Http request headers added to all request. Example: '[{"Authorization": "SuperSecret"}, {"Auth2": "asd"}]'

```

## Usage examples:

### Installed package

Start the sample application (install the necessary packages listed in test/requirements_for_test.txt):

```shell
$ python3 test/test_application.py
```
Start the fuzzer:

```shell
$ APIFuzzer -s test/test_api/openapi_v2.json -u http://127.0.0.1:5000/ -r /tmp/reports/ --log debug 
```
Check the reports:

```shell
$ ls -1 /tmp/reports/
```
Report example:

```shell
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

### Docker

#### Tested service runs on docker host

Notes 
> * Use  http://host.docker.internal instead of http://127.0.0.1 or http://localhost in the references. Read [Docker cocumentation](https://docs.docker.com/desktop/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host) for further explanation
> * You need to attach a volume like in this example to share files and folders with the container:

```shell
docker run --volume results:/results/ kisspeter/apifuzzer --src_url http://host.docker.internal:8000/openapi.json --url http://host.docker.internal:8000 --test_report /results/junit.xml --report /results/report/ ```
```
#### Tested service runs in other docker container
Notes 
> * Define `--net` at startup to attach this docker to an existing network. Read [Docker cocumentation](https://docs.docker.com/network/network-tutorial-standalone/#use-user-defined-bridge-networks) for further explanation
> * Use  http://CONTAINERNAME instead of http://127.0.0.1 or http://localhost in the references. 
> * You need to attach a volume like in this example to share files and folders with the container:

```shell
docker run --volume results:/results/ kisspeter/apifuzzer --net fastapi-performance-optimization_default kisspeter/apifuzzer --src_url http://fastapi-performance-optimization:8000/openapi.json -u http://fastapi-performance-optimization:8000 --test_report /results/junit.xml --report /results/report/```
```

[API Blueprint]: https://apiblueprint.org/
[Swagger]: http://swagger.io/
[OpenAPI]: https://swagger.io/docs/specification/about/
[GraphQL]: https://graphql.org/

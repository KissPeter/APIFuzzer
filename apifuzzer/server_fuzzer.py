from __future__ import print_function
import json
from kitty.fuzzers import ServerFuzzer
from kitty.model import Container
from utils import get_field_type_by_method
from kitty.data.report import Report


def _flatten_dict_entry(orig_key, v):
    entries = []
    if isinstance(v, list):
        for i in range(len(v)):
            entries.extend(_flatten_dict_entry('%s[%s]' % (orig_key, i), v[i]))
    elif isinstance(v, dict):
        for k in v:
            entries.extend(_flatten_dict_entry('%s/%s' % (orig_key, k), v[k]))
    else:
        entries.append((orig_key, v))
    return entries


class OpenApiServerFuzzer(ServerFuzzer):
    """Extends the ServerFuzzer with exit after the end message."""

    def not_implemented(self, func_name):
        pass

    def __init__(self, logger=None):
        super(OpenApiServerFuzzer, self).__init__(logger=logger)

    def _end_message(self):
        super(OpenApiServerFuzzer, self)._end_message()
        # Sometimes Kitty has stopped the fuzzer before it has finished the work. We can't continue, but can log
        self.logger.info('Stop fuzzing session_info: {}'.format(self.session_info.as_dict()))
        test_list_str_end = self.session_info.as_dict().get('test_list_str', '0-0').split('-', 1)[1].strip()
        if self.session_info.as_dict().get('end_index') != int(test_list_str_end):
            self.logger.error('Fuzzer want to exit before the end of the tests')
        self._exit_now(None, None)

    def _transmit(self, node):
        payload = {}
        for key in ('url', 'method', 'headers'):
             payload[key] = node.get_field_by_name(key).render().tobytes()
        fuzz_place = get_field_type_by_method(node.get_field_by_name('method')._default_value)
        payload[fuzz_place] = self._recurse_params(node.get_field_by_name(fuzz_place))
        self._last_payload = payload
        try:
            return self.target.transmit(**payload)
        except Exception as e:
            self.logger.error('Error in transmit: %s', e)
            raise

    @staticmethod
    def _recurse_params(param):
        _return = dict()
        if type(param) != Container:
            _return = param.render().tobytes()
        else:
            for field in param._fields:
                _return[field.get_name()] = OpenApiServerFuzzer._recurse_params(field)
        return _return

    def _store_report(self, report):
        self.logger.debug('<in>')
        report.add('test_number', self.model.current_index())
        report.add('fuzz_path', self.model.get_sequence_str())
        test_info = self.model.get_test_info()
        data_model_report = Report(name='Data Model')
        for k, v in test_info.items():
            new_entries = _flatten_dict_entry(k, v)
            for (k_, v_) in new_entries:
                data_model_report.add(k_, v_)
        report.add(data_model_report.get_name(), data_model_report)
        payload = self._last_payload
        if payload is not None:
            data_report = Report('payload')
            data_report.add('raw', payload)
            data_report.add('hex', json.dumps(payload).encode('hex'))
            data_report.add('length', len(payload))
            report.add('payload', data_report)
        else:
            report.add('payload', None)

        self.dataman.store_report(report, self.model.current_index())
        self.dataman.get_report_by_id(self.model.current_index())

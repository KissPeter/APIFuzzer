from kitty.data.report import Report
from kitty.fuzzers import ServerFuzzer
from kitty.model import Container, KittyException

from apifuzzer.utils import get_logger, transform_data_to_bytes


def _flatten_dict_entry(orig_key, v):
    """
    This function is called recursively to list the params in template
    :param orig_key: original key
    :param v: list of params
    :rtype: list
    """
    entries = []
    if isinstance(v, list):
        count = 0
        for elem in v:
            entries.extend(_flatten_dict_entry('%s[%s]' % (orig_key, count), elem))
            count += 1
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

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info('Logger initialized')
        super(OpenApiServerFuzzer, self).__init__(logger=self.logger)

    def _transmit(self, node):
        """
        Where the magic happens. This function prepares the request
        :param node: Kitty template
        :type node: object
        """
        payload = {'content_type': self.model.content_type}
        for key in ['url', 'method']:
            payload[key] = transform_data_to_bytes(node.get_field_by_name(key).render())
        fuzz_places = ['params', 'headers', 'data', 'path_variables']
        for place in fuzz_places:
            try:
                if place in node._fields_dict:
                    param = node.get_field_by_name(place)
                    _result = self._recurse_params(param)
                    payload[place] = _result
            except KittyException as e:
                self.logger.warning(f'Exception occurred while processing {place}: {e}')
        self._last_payload = payload
        try:
            return self.target.transmit(**payload)
        except Exception as e:
            self.logger.error(f'Error in transmit: {e}')
            raise e

    @staticmethod
    def _recurse_params(param):
        """
        Iterates trough parameters recursively
        :param param: param to process
        :type param: object
        :rtype: dict
        """
        _return = dict()
        if isinstance(param, Container):
            for field in param._fields:
                _return[field.get_name()] = OpenApiServerFuzzer._recurse_params(field)
        elif hasattr(param, 'render'):
            _return = transform_data_to_bytes(param.render()).decode(errors='ignore')
        return _return

    def _store_report(self, report):
        """
        Enrich fuzz report
        :param report: report to extend
        """
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
            data_report.add('length', len(payload))
            report.add('payload', data_report)
        else:
            report.add('payload', None)

        self.dataman.store_report(report, self.model.current_index())
        # TODO investigate:
        #  self.dataman.get_report_by_id(self.model.current_index())

    def _test_environment(self):
        """
        Checks the test environment - not used
        """
        sequence = self.model.get_sequence()
        try:
            if self._run_sequence(sequence):
                self.logger.info('Environment test failed')
        except Exception:
            self.logger.info('Environment test failed')

from kitty.data.report import Report
import six

from apifuzzer.utils import try_b64encode


class Apifuzzer_report(Report):

    def __init__(self, name):
        super().__init__(name)

    def to_dict(self, encoding='base64'):
        '''
        Return a dictionary version of the report

        :param encoding: required encoding for the string values (default: 'base64')
        :rtype: dictionary
        :return: dictionary representation of the report
        '''
        res = {}
        for k, v in self._data_fields.items():
            if isinstance(v, (bytes, bytearray, six.string_types)):
                #v = StrEncodeEncoder(encoding).encode(v).tobytes().decode()
                v = try_b64encode(v)
            res[k] = v
        for k, v in self._sub_reports.items():
            res[k] = v.to_dict(encoding)
        return res


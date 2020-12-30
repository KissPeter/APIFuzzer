import six
from bitstring import Bits
from kitty.core import kassert
from kitty.model import RandomBits, String, BaseField
from kitty.model.low_level.encoder import ENC_BITS_DEFAULT, strToBytes

from apifuzzer.utils import secure_randint, get_logger


class Utf8Chars(BaseField):
    """
    This custom fuzzer iterates through the UTF8 chars and gives back random section between min and max length
    Highly relies on random numbers so most probably will give you different values each time to run it.

    You can generate the chars like this:
    for st in range(0, 1114111):
    try:
        print('{}-> {}'.format(st, chr(st)))
    except (UnicodeEncodeError, ValueError):
        pass
    Above 1114111 chars started to getting unprocessable so this is the upper limit for now.

    """
    MAX = 1114111

    def __init__(self, value, name, fuzzable=True, min_length=20, max_length=100, num_mutations=80):
        super(BaseField, self).__init__(name=name)
        self.logger = self.logger = get_logger(self.__class__.__name__)
        self.name = name
        self.value = value
        self.min_length = min_length
        self.max_length = max_length
        self._num_mutations = num_mutations
        self.position = self.init_position()
        self._initialized = False
        self._default_value = self.to_bits(chr(self.MAX))
        self._encoder = ENC_BITS_DEFAULT
        self._default_rendered = self._encode_value(self._default_value)
        self._hash = None
        self._fuzzable = fuzzable
        self._need_second_pass = False
        self._controlled = False

    def init_position(self):
        return secure_randint(0, self.MAX)

    @staticmethod
    def str_to_bytes(value):
        """
        :type value: ``str``
        :param value: value to encode
        """
        kassert.is_of_types(value, (bytes, bytearray, six.string_types))
        if isinstance(value, six.string_types):
            return value.encode(encoding='utf-8')
        if isinstance(value, bytearray):
            return bytes(value)
        return value

    def to_bits(self, val):
        return Bits(self.str_to_bytes(val))

    def _mutate(self):

        current_value = list()
        current_mutation_length = secure_randint(self.min_length, self.max_length)
        for st in range(self.position, self.position + current_mutation_length):
            current_value.append(chr(st))
        self._current_value = self.to_bits("".join(current_value))
        self.position += current_mutation_length
        if self.position > self.MAX:
            self.position = self.init_position()

    def __str__(self):
        return f'{self.name}->{self.value}'

    def __repr__(self):
        return f'{self.name}->{self.value}'


class RandomBitsField(RandomBits):
    """
    Creates a fields which compatible field with String and Delimiter
    https://lcamtuf.blogspot.hu/2014/08/binary-fuzzing-strategies-what-works.html

    """

    def not_implemented(self, func_name):
        pass

    def __init__(self, value, name, fuzzable=True):
        self.name = name
        self.value = value
        super(RandomBitsField, self).__init__(name=name, value=value, min_length=20, max_length=100, fuzzable=fuzzable,
                                              num_mutations=80)

    def _mutate(self):
        if self._step:
            length = self._min_length + self._step * self._current_index
        else:
            length = self._random.randint(self._min_length, self._max_length)
        current_bytes = ''
        for _ in range(length // 8 + 1):
            current_bytes += chr(self._random.randint(0, 255))
        self._current_value = Bits(bytes=strToBytes(current_bytes))[:length]

    def __str__(self):
        return f'{self.name}->{self.value}'

    def __repr__(self):
        return f'{self.name}->{self.value}'


class UnicodeStrings(String):

    def __init__(self, value, name, min_length=20, max_length=100, num_mutations=80, fuzzable=True):
        self.min_length = min_length
        self.max_length = max_length
        self._num_mutations = num_mutations
        self.name = name
        self.value = value
        super(UnicodeStrings, self).__init__(name=name, value=value, fuzzable=fuzzable)

    def not_implemented(self, func_name):
        pass

    def __str__(self):
        return f'{self.name}->{self.value}'

    def __repr__(self):
        return f'{self.name}->{self.value}'

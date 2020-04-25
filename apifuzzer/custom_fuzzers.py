from random import randint

from bitstring import Bits
from kitty.model import RandomBits, String, BaseField
from kitty.model.low_level.encoder import ENC_BITS_DEFAULT


# https://lcamtuf.blogspot.hu/2014/08/binary-fuzzing-strategies-what-works.html


class Utf8Chars(BaseField):
    MAX = 1114111

    def __init__(self, value, name, fuzzable=True, min_length=20, max_length=100, num_mutations=80):
        super(BaseField, self).__init__(name=name)
        self.min_length = min_length
        self.max_length = max_length
        self._num_mutations = num_mutations
        self.position = randint(0, self.MAX)
        self._initialized = False
        self._default_value = self.to_bits(chr(self.MAX))
        self._encoder = ENC_BITS_DEFAULT
        self._default_rendered = self._encode_value(self._default_value)
        self._hash = None
        self._fuzzable = fuzzable
        self._need_second_pass = False
        self._controlled = False

    def to_bits(self, val):
        return Bits(bytes(val, 'utf-16'))

    def _mutate(self):
        current_value = list()
        current_mutation_length = randint(self.min_length, self.max_length)
        for st in range(self.position, current_mutation_length):
            current_value.append(chr(st))
        self._current_value = self.to_bits("".join(current_value))
        self.position += current_mutation_length


class RandomBitsField(RandomBits):
    """Creates a fields which compatible field with String and Delimiter"""

    def not_implemented(self, func_name):
        pass

    def __init__(self, value, name, fuzzable=True):
        super(RandomBitsField, self).__init__(name=name, value=value, min_length=20, max_length=100, fuzzable=fuzzable,
                                              num_mutations=80)


class UnicodeStrings(String):

    def __init__(self, value, name, min_length=20, max_length=100, num_mutations=80, fuzzable=True):
        self.min_length = min_length
        self.max_length = max_length
        self.num_mutations = num_mutations
        super(UnicodeStrings, self).__init__(name=name, value=value, fuzzable=fuzzable)

    def not_implemented(self, func_name):
        pass

    def _mutate(self):
        pass

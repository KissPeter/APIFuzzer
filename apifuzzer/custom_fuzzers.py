from kitty.model import RandomBits, String


# https://lcamtuf.blogspot.hu/2014/08/binary-fuzzing-strategies-what-works.html


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

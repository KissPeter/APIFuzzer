from kitty.model import RandomBits


class RandomBitsField(RandomBits):
    """Creates a fields which compatible field with String and Delimiter"""

    def not_implemented(self, func_name):
        pass

    def __init__(self, value, name, fuzzable=True):
        super(RandomBitsField, self).__init__(name=name, value=value, min_length=20, max_length=100, fuzzable=fuzzable, num_mutations=80)

from apifuzzer.__init__ import __version__

PROJECT = 'APIFuzzer'


def get_version():
    return '{} {}'.format(PROJECT, __version__)

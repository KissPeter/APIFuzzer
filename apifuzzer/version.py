from apifuzzer.__init__ import __version__

PROJECT = 'APIFuzzer'


def get_version():
    """
    Provides name and version of the application
    :rtype: str
    """
    return '{} {}'.format(PROJECT, __version__)

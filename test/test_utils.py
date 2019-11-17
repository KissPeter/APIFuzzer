import os

import psutil


def get_test_server_pid():
    _return = None
    for proc in psutil.net_connections('tcp4'):
        if proc.laddr.port == 5000:
            _return = proc.pid
            print('Found process: {}'.format(proc))
            break
    print('No process found which listens on port 5000')
    return _return


def stop_test_server():
    os.kill(get_test_server_pid(), 9)

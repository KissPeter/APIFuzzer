import os

import psutil


def get_test_server_pid(call=None):
    _return = list()
    for proc in psutil.net_connections('tcp4'):
        if proc.laddr.port == 5000 and proc.pid:
            _return.append(proc.pid)
            print('{} - found process: {}'.format(call, proc.pid))
    if len(_return) < 1:
        print('{} - no process found which listens on port 5000'.format(call))
    return _return


def stop_test_server():
    for pid in get_test_server_pid("Stop"):
        if pid:
            os.kill(pid, 9)

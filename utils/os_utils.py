"""
The original version of this file can be found at:

https://github.com/ecbftw/nanown/blob/master/trunk/lib/nanownlib/platform.py

And licensed under GLPv3.

All these functions make the tool Linux specific.
"""
import time
import multiprocessing

from ctypes import cdll, c_int, byref


def setCPUAffinity():
    """
    :note: Child processes inherit the parent's affinity.
    """
    cpus = multiprocessing.cpu_count()
    libc = cdll.LoadLibrary("libc.so.6")

    # Using zero as first parameter means "self PID"
    res = libc.sched_setaffinity(0, 4, byref(c_int(0x00000001 << (cpus - 1))))

    # Give our process a chance to migrate to a different CPU if necessary
    time.sleep(0.25)
    return res


def setTCPTimestamps(enabled=True):
    with open('/proc/sys/net/ipv4/tcp_timestamps', 'r+b') as fh:
        ret_val = fh.read(1) == b'1'
        fh.seek(0)
        if enabled:
            fh.write(b'1')
        else:
            fh.write(b'0')
    return ret_val


previous_governors = None


def setPowersave(enabled):
    """
    http://superuser.com/a/454104

    Also mentioned in https://github.com/seecurity/mona-timing-lib
    as "Disable Intel Speedstep"



    :param enabled: Send powersave to scaling governor?
    :return: None
    """

    global previous_governors
    cpus = multiprocessing.cpu_count()
    if enabled:
        if previous_governors is None:
            previous_governors = [b"powersave"] * cpus
        new_governors = previous_governors
    else:
        new_governors = [b"performance"] * cpus

    previous_governors = []
    for c in range(cpus):
        with open('/sys/devices/system/cpu/cpu%d/cpufreq/scaling_governor' % c,
                  'r+b') as fh:
            previous_governors.append(fh.read())
            fh.seek(0)
            fh.write(new_governors[c])


def setLowLatency(enabled):
    with open('/proc/sys/net/ipv4/tcp_low_latency', 'r+b') as fh:
        ret_val = fh.read(1) == b'1'
        fh.seek(0)
        if enabled:
            fh.write(b'1')
        else:
            fh.write(b'0')
    return ret_val

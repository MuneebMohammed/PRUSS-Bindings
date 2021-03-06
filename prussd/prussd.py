#!/usr/bin/python3

# prussd.py - Daemon to process PRU access requests
#                for non-root processes
#
# Copyright (c) 2018 Mohammed Muneeb
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#

import errno
import os
import select
import shutil
import stat
import socketserver
import subprocess
import threading

class paths:
    CONFIG_FILE = "/etc/default/prussd.conf"
    SOCK_FILE = "/tmp/prussd.sock"
    RPROC_SYSFS_PATH = "/sys/class/remoteproc/remoteproc"
    RPROC_DEBUGFS_PATH = "/sys/kernel/debug/remoteproc/remoteproc"
    FIRMWARE_PATH = "/lib/firmware"
    MODPROBE_PATH = "/sbin/modprobe"
    RPMSG_CHANNELS = ["rpmsg_pru"]
    FIRMWARE_PATHS = [FIRMWARE_PATH]


def rproc_sysfs(attr, number):
    """Returns the appropriate remoteproc sysfs entry."""
    return os.path.normpath(paths.RPROC_SYSFS_PATH+str(number+1)+"/"+attr)

def rproc_debugfs(attr, number):
    """Returns the corresponding remoteproc debugfs entry."""
    return os.path.normpath(paths.RPROC_DEBUGFS_PATH+str(number+1)+"/"+attr)

def rpmsg_devnode(chan_name, chan_port):
    """Return the corresponding device node entry for the rpmsg channel."""
    return os.path.normpath("/dev/"+chan_name+str(chan_port))

def sysfs_read(path):
    """Util function to read from a file."""
    if not os.path.exists(path):
        return -errno.ENOENT
    try:
        with open(path, 'r') as fd:
            return fd.read()
    except OSError as err:
        return -err.errno


def sysfs_write(path, val):
    """Util function to write to a file."""
    if not os.path.exists(path):
        return -errno.ENOENT

    try:
        with open(path, 'w') as fd:
            fd.write(str(val))
        return 0
    except OSError as err:
        return -err.errno


def set_config():
    """Reads the Daemon config file and sets paths accordingly."""
    if not os.path.exists(paths.CONFIG_FILE):
        return
    try:
        with open(paths.CONFIG_FILE, "r") as fd:
            for line in fd.readlines():
                [key, values] = line.strip().split("=")
                key = key.strip()
                values = values.split()

                if key == "FIRMWARE":
                    paths.FIRMWARE_PATHS += values
                elif key == "RPMSG_CHANNELS":
                    paths.RPMSG_CHANNELS += values
                else:
                    pass
    except OSError:
        pass

def mod_probe(mod_name, probe=True):
    """Probes/Removes the appropriate kernel driver module."""
    try:
        if probe:
            subprocess.Popen([paths.MODPROBE_PATH, mod_name]).wait()
        else:
            subprocess.Popen([paths.MODPROBE_PATH, "-r", mod_name]).wait()
        return 0
    except OSError as err:
        return -err.errno


def load_firmware(number, cmd):
    """Moves the firmware to /lib/firmware and modifies the firmware attribute."""
    if len(cmd) > 2:
        return -errno.EINVAL

    if not os.path.exists(cmd[1]):
        return -errno.ENOENT

    if not any(cmd[1].startswith(path) for path in paths.FIRMWARE_PATHS):
        return -errno.EPERM

    try:
        fname = cmd[1].split("/")[-1]
        fw_path = paths.FIRMWARE_PATH+"/"+fname
        if cmd[1] != fw_path:
            shutil.copyfile(os.path.normpath(cmd[1]), os.path.normpath(fw_path))
        return sysfs_write(rproc_sysfs("firmware", number), fname)
    except OSError as err:
        return -err.errno


def get_msg(cmd):
    """Reads the character device file of the rpmsg channel: Non-Blocking."""
    if len(cmd) != 3:
        return -errno.EINVAL
    try:
        chan_name = str(cmd[1])
        chan_port = int(cmd[2])
    except ValueError:
        return -errno.EINVAL

    rpmsg_dev = rpmsg_devnode(chan_name, chan_port)
    if chan_name not in paths.RPMSG_CHANNELS:
        return -errno.EPERM
    if not os.path.exists(rpmsg_dev):
        return -errno.ENODEV
    try:
        reply = ''
        with open(rpmsg_dev, 'r') as fd:
            #timeout 0 in select => non-blocking read
            while fd in select.select([fd], [], [], 0)[0]:
                reply += fd.readline()
        if reply == '':
            return '\n'
        return reply
    except OSError as err:
        return -err.errno


def send_msg(cmd):
    """Sends a message on the specified rpmsg channel."""
    if len(cmd) < 4:
        return -errno.EINVAL
    try:
        chan_name = str(cmd[1])
        chan_port = int(cmd[2])
    except ValueError:
        return -errno.EINVAL

    rpmsg_dev = rpmsg_devnode(chan_name, chan_port)
    if chan_name not in paths.RPMSG_CHANNELS:
        return -errno.EPERM
    if not os.path.exists(rpmsg_dev):
        return -errno.ENODEV
    try:
        with open(rpmsg_dev, 'w') as fd:
            fd.write(' '.join(cmd[3:])+'\n')
            return 0
    except OSError as err:
        return -err.errno


def event_wait(cmd):
    """Waits for an event on the specified rpmsg channel."""
    cmd_length = len(cmd)
    if cmd_length != 3 and cmd_length != 4:
        return -errno.EINVAL
    try:
        chan_name = str(cmd[1])
        chan_port = int(cmd[2])
        if cmd_length == 4:
            timeout = int(cmd[3])
    except ValueError:
        return -errno.EINVAL
    rpmsg_dev = rpmsg_devnode(chan_name, chan_port)
    if chan_name not in paths.RPMSG_CHANNELS:
        return -errno.EPERM
    if not os.path.exists(rpmsg_dev):
        return -errno.ENODEV
    try:
        with open(rpmsg_dev, 'r') as fd:
            if cmd_length == 3: #indefinite wait, no timeout specified
                select.select([fd], [], [])
                return 0
            else:
                return 0 if select.select([fd], [], [], timeout)[0] else -errno.ETIME
    except OSError as err:
        return -err.errno

class PRURequestHandler(socketserver.StreamRequestHandler):
    """
    The request handler class for our socket server
    Overrides the handle method of the BaseRequestHandler class to implement
    communication with the socket file.
    """

    def handle(self):

        # self.rfile is a file-like object created by the StreamRequestHandler
        self.data = self.rfile.readline().strip()

        #decode bytes into string and get command args
        cmd = self.data.decode("utf-8").split()

        #dict mapping commands to functions
        cmds = {
            "PROBE_RPROC": lambda: mod_probe("pru_rproc"),
            "UNPROBE_RPROC": lambda: mod_probe("pru_rproc", False),
            "ENABLE_0": lambda: sysfs_write(rproc_sysfs("state", 0), "start"),
            "ENABLE_1": lambda: sysfs_write(rproc_sysfs("state", 1), "start"),
            "DISABLE_0": lambda: sysfs_write(rproc_sysfs("state", 0), "stop"),
            "DISABLE_1": lambda: sysfs_write(rproc_sysfs("state", 1), "stop"),
            "PAUSE_0": lambda: sysfs_write(rproc_debugfs("single_step", 0), 1),
            "PAUSE_1": lambda: sysfs_write(rproc_debugfs("single_step", 1), 1),
            "RESUME_0": lambda: sysfs_write(rproc_debugfs("single_step", 0), 0),
            "RESUME_1": lambda: sysfs_write(rproc_debugfs("single_step", 1), 0),
            "STATE_0": lambda: sysfs_read(rproc_sysfs("state", 0)),
            "STATE_1": lambda: sysfs_read(rproc_sysfs("state", 1)),
            "GETREGS_0": lambda: sysfs_read(rproc_debugfs("regs", 0)),
            "GETREGS_1": lambda: sysfs_read(rproc_debugfs("regs", 1)),
            "LOAD_0": lambda: load_firmware(0, cmd),
            "LOAD_1": lambda: load_firmware(1, cmd),
            "GETMSG": lambda: get_msg(cmd),
            "SENDMSG": lambda: send_msg(cmd),
            "EVENTWAIT": lambda: event_wait(cmd)
            }

        resp = cmds[cmd[0]]() if cmd[0] in cmds else -errno.EINVAL
        self.wfile.write(bytes(str(resp), "utf-8"))

class ThreadedPRUServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    pass


if __name__ == "__main__":

    # if socket exists, unlink/remove it
    try:
        os.remove(paths.SOCK_FILE)
    except OSError:
        pass

    # read config file
    set_config()

    # Create the server, binding to the socket file
    server = ThreadedPRUServer(paths.SOCK_FILE, PRURequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    # Change socket file permissions
    os.chmod(paths.SOCK_FILE, stat.S_IRWXO)

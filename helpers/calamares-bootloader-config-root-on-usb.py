#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

__author__      = 'Kel Modderman'
__copyright__   = '(C) 2024 Kel Modderman <kelvmod@gmail.com>'
__license__     = 'GPLv2 or any later version'
__description__ = 'Return 0 if / and /boot/efi on a USB bus device'

import pyudev
import sys

def get_device_mounted_on(mount_pnt):
    with open('/proc/mounts', 'r') as mounts:
        entries = mounts.readlines()
        for entry in entries:
            device, mount = entry.split()[:2]
            if (mount == mount_pnt):
                return device

    return None

def run(child_device_node=None):
    if child_device_node is None:
        sys.exit(1)

    context = pyudev.Context()
    root_device = pyudev.Devices.from_device_file(context, child_device_node)
    try:
        parent_device_node = root_device.find_parent('block').device_node
    except AttributeError as e:
        parent_device = root_device
    else:
        parent_device = pyudev.Devices.from_device_file(context, parent_device_node)

    parent_bus = parent_device.get('ID_BUS')
    if parent_bus is None or parent_bus != 'usb':
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    try:
        root = sys.argv[1]
    except IndexError:
        root = get_device_mounted_on('/')
    run(root)

    try:
        boot = sys.argv[1]
    except IndexError:
        boot = get_device_mounted_on('/boot/efi')
    run(boot)

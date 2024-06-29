#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2022 Marvell International Ltd. 
# All Rights Reserved.
#
# This file contains information that is confidential and proprietary to Marvell International Ltd. Commercial use of 
# this code is subject to licensing terms and is permitted only on semiconductor devices manufactured by or on behalf 
# of Marvell International Ltd or its affiliates. Distribution subject to written consent from Marvell International Ltd.
#
######################################################################################################################

import pytest
import sfvs.click as click
from sfvs.device.device_factory import DeviceFactory
from sfvs.command.firmware.downfw_cmd import *
import datetime
import subprocess
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')

@pytest.fixture(scope="module")
def check_device(request):
    subprocess.check_call(["sudo","modprobe","nvme"]) 
    disk_type = request.config.getoption('device_type')
    process = subprocess.Popen(["sudo","fdisk","-l"],stdout=subprocess.PIPE)
    out, err = process.communicate()
    disk = ''
    #print(out)
    if disk_type == "sata":
        disk = "/dev/sdb"
        if not (disk in str(out)):
            logging.warning("Cannot find the second sata disk")
            sys.exit()
    if disk_type == "nvme":
        disk = "/dev/nvme0n1"
        if not (disk in str(out)):
            logging.warning("Cannot find nvme disk")
            sys.exit()
    yield disk
    

def pytest_addoption(parser):
    parser.addoption("--device_type", default = 'nvme', dest = "device_type", help = "device type, sata or nvme")
    parser.addoption("--size", dest = "size", default = "1", help = "read/write size, default is 1 GiB.")

def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".

    device_type_value = metafunc.config.getoption("device_type")
    size_value = metafunc.config.getoption("size")

   
    if "device_type" in metafunc.fixturenames and device_type_value is not None:
        metafunc.parametrize("device_type", [device_type_value])

    if "size" in metafunc.fixturenames and size_value is not None:
        metafunc.parametrize("size", [size_value])


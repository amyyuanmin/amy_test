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
import sys
import subprocess
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')


@pytest.fixture(scope="module")
def check_device(request):
    subprocess.check_call(["sudo", "modprobe", "nvme"])
    disk_type = request.config.getoption('disk_type')
    process = subprocess.Popen(["sudo", "fdisk", "-l"], stdout=subprocess.PIPE)
    out, _ = process.communicate()
    disk = ''
    logging.info(out)
    if disk_type == "sata":
        disk = "/dev/sdb"
        if not (disk in str(out)):
            logging.info("Cannot find the second sata disk")
            sys.exit()
    if disk_type == "nvme":
        disk = "/dev/nvme0n1"
        if not (disk in str(out)):
            logging.info("Cannot find nvme disk")
            sys.exit()
    yield disk


def pytest_addoption(parser):
    #parser.addoption("--fwver", action="store", default='', help="list of stringinputs to pass to test functions")
    #parser.addoption("--sn", action="store", default='12345678', help="list of stringinputs to pass to test functions")
    #parser.addoption("--mn", action="store", default='MRVL 1098 PART0', help="list of stringinputs to pass to test functions")
    #parser.addoption("--sector", action="store", default='500139360', help="The sector size, defaute is 256G sector number")
    parser.addoption("--cfg", action="store", default='', help="cfg file")
    parser.addoption("--device_type", default='nvme', dest="device_type", help="device type, sata or nvme")
    #parser.addoption("--test_loop", action="store", default="10000", help="The counts of the loops for the testing. Default value is 10000 loops")
    #parser.addoption( "--test_runtime", action="store", default="72", help="The run time for the test(seconds). Default is 72 hours")


@pytest.fixture(scope='module')
def device_type(request):
    device_type = request.config.getoption('device_type')
    return device_type


@pytest.fixture(scope='module')
def cfg(request):
    cfg = request.config.getoption('cfg')
    return cfg
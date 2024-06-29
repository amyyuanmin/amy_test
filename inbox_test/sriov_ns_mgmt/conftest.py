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
import os
from sfvs.nvme import nvme
import logging

def pytest_addoption(parser):
    parser.addoption(
        "--vf_amount",  # Do parameterize from RPI to used for all test cases
        dest="vf_amount",
        action="store", 
        default="32",
        help="The amount of VF for test"
    )
    parser.addoption(
        "--rpi_ip",
        action="store",
        default=None,
        help="RPI IP, used to send UART cmd"
    )
    parser.addoption(
        "--rpi_path",
        action="store",
        default="",
        help="Scripts path on RPI, used to power cycle the board"
    )

@pytest.fixture(scope="module")
def host():
    try:
        host = nvme.Host.enumerate()[0]
    except Exception as e:
        pytest.fail("Failed to initialize host: {}".format(e))
    return host

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope='class')
def vf_amount(request):
    vf_amount = request.config.getoption('vf_amount')
    return int(vf_amount)

@pytest.fixture(scope='module')
def rpi_ip(request):
    rpi_ip = request.config.getoption('rpi_ip')
    return rpi_ip

@pytest.fixture(scope='module')
def rpi_path(request):
    rpi_path = request.config.getoption('rpi_path')
    return rpi_path
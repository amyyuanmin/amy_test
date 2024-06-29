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
import logging

def pytest_addoption(parser):
    parser.addoption(
        "--pf_amount",  # Do parameterize from RPI since reboot required for each PF amount.
        dest="pf_amount",
        action="store", 
        default="16",
        help="The amount of PF for test, at least 2"
    )

    parser.addoption(
        "--build",  
        dest="build",
        action="store", 
        default="E2e",
        help="The build to be tested, Ramdrive or E2e"
    )

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope='class')
def pf_amount(request):
    pf_amount = request.config.getoption('pf_amount')
    return int(pf_amount)

@pytest.fixture(scope='class')
def build(request):
    build = request.config.getoption('build')
    return build
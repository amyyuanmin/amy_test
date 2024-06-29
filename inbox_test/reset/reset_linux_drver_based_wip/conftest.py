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
import logging
import os

def pytest_addoption(parser):
    parser.addoption(
        "--loop", action="store", default="500", help="how many loops will be executed for test"
    )

    #below for multiple namespace related
    parser.addoption(
        "--func_amount", action="store", default="16", help="Function amount for SRIOV or Multi-PF, default is 16 which refer to Multi-PF without ARI enabled"
    )

@pytest.fixture(scope="function")
def loop(request):
    return request.config.getoption("--loop")

@pytest.fixture(scope="session")
def func_amount(request):
    return request.config.getoption("--func_amount")

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

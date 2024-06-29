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
from sfvs.nvme import nvme

def pytest_addoption(parser):
    parser.addoption(
        "--zone_amount",
        action="store",
        default="4",
        help="How many zones defined, 4 is pre-defined"
    )
    parser.addoption(
        "--build",
        action="store",
        default="E2e",
        help="Which build for test, Ramdrive or E2e"
    )
    
@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope="module")
def zone_amount(request):
    return request.config.getoption("--zone_amount")

@pytest.fixture(scope="module")
def build(request):
    return request.config.getoption("--build")

@pytest.fixture(scope="module")
def host():
    try:
        host = nvme.Host.enumerate()[0]
    except Exception as e:
        pytest.fail("Failed to initialize host: {}".format(e))
    return host

@pytest.fixture(scope='module')
def controller(host, request):
    try:
        controller = host.controller.enumerate()[0]
    except Exception as e:
        pytest.fail("Failed to initialize controller: {}".format(e))
    def fin():
        controller.__exit__(None, None, None)

    request.addfinalizer(fin)

    return controller.__enter__()

@pytest.fixture(scope='module')
def namespace(controller, request):
    try:
        namespace = controller.enumerate_namespace()[0]
    except Exception as e:
        pytest.fail("Failed to initialize namespace: {}".format(e))

    def fin():
        namespace.__exit__(None, None, None)

    request.addfinalizer(fin)

    return namespace.__enter__()

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
        "--format_lbaf", 
        action="store", 
        choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"], 
        help="LBA size to be formated, default is 1, i.e. 4K."
        ) 
    parser.addoption(
        "--project", 
        action="store",
        default="vega",
        help="The project is used for checking the vail or vega project type."
        )

@pytest.fixture(scope='module')
def format_lbaf(request):
    format_lbaf = request.config.getoption('format_lbaf')
    return format_lbaf

@pytest.fixture(scope="module")
def project(request):
    return request.config.getoption("--project")

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

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name
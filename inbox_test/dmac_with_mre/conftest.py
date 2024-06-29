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
        "--buffer_addr", 
        action="store", 
        help="Ram driver buffer starting address"
        )
    parser.addoption(
        "--lbaf", 
        action="store", 
        help="The test under which LBAF"
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
    parser.addoption(
        "--fw_log_indicator",
        action="store",
        default="fw_log.log",
        help="Fw log name"
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
def buffer_addr(request):
    return request.config.getoption("--buffer_addr")

@pytest.fixture(scope="module")
def lbaf(request):
    return request.config.getoption("--lbaf")

@pytest.fixture(scope='module')
def rpi_ip(request):
    rpi_ip = request.config.getoption('rpi_ip')
    return rpi_ip

@pytest.fixture(scope='module')
def rpi_path(request):
    rpi_path = request.config.getoption('rpi_path')
    return rpi_path

@pytest.fixture(scope="module")
def fw_log_indicator(request):
    return request.config.getoption("--fw_log_indicator")
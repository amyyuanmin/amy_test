#!/usr/bin/python
import pytest
import os
import logging

def pytest_addoption(parser):
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

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope='module')
def rpi_ip(request):
    rpi_ip = request.config.getoption('rpi_ip')
    return rpi_ip

@pytest.fixture(scope='module')
def rpi_path(request):
    rpi_path = request.config.getoption('rpi_path')
    return rpi_path
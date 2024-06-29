#!/usr/bin/python
import pytest
import os
from sfvs.nvme import nvme
import logging

def pytest_addoption(parser):
    parser.addoption(
            "--scenario",
            action="store",
            default="single_pf",
            help="Boot partition under which scenario, single-pf, multi-pf or SRIOV"
        )

@pytest.fixture(scope="module")
def host():
    try:
        host = nvme.Host.enumerate()[0]
    except Exception as e:
        pytest.fail("Failed to initialize host: {}".format(e))
    return host

@pytest.fixture(scope='module')
def controller(host):
    try:
        controller = host.controller.enumerate()[0]
    except Exception as e:
        pytest.fail("Failed to initialize controller: {}".format(e))

    return controller

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope="module")
def scenario(request):
    return request.config.getoption("--scenario")
#!/usr/bin/python
import pytest
from configparser import ConfigParser
import os, sys
import logging
from sfvs.nvme import nvme

def pytest_addoption(parser):# only for test_fio
    parser.addoption(
        "--case_suite",
        dest="case_suite",
        required=True,
        help="case suite to be executed."
    )
    parser.addoption(
        "--lba_size", 
        action="store", 
        default="4k", 
        help="LBA size to be formated, default is 4k."
        ) 
    parser.addoption(
        "--dry_run", 
        action="store", 
        default=False, 
        help="debug purpose, if True, only print cmd but not execute them."
        ) 
    parser.addoption(
        "--perf", 
        action="store", 
        default="False",  # RPI transfer this value to testbed which is a string via ssh 
        help="Performance test or not, if so, will collect perf data"
        ) 
    parser.addoption(
        "--mofify_folder_name", 
        action="store", 
        default="False",  
        help="Modify log folder name"
        ) 
    parser.addoption(
        "--need_format", 
        action="store", 
        default="False",  
        help="format before write"
        ) 
    parser.addoption(
        "--lbaf", 
        action="store", 
        default="0", 
        help="LBA Format: This field specifies the LBA format to apply to the NVM media. Defaults to 0."
        ) 
    

@pytest.fixture(scope='class')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope='class')
def dry_run(request):
    dry_run = request.config.getoption('dry_run')
    return dry_run

@pytest.fixture(scope='class')
def perf(request):
    perf = request.config.getoption('perf')
    return perf

@pytest.fixture(scope='class')
def mofify_folder_name(request):
    mofify_folder_name = request.config.getoption('mofify_folder_name')
    return mofify_folder_name

@pytest.fixture(scope='class')
def need_format(request):
    need_format = request.config.getoption('need_format')
    return need_format

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
#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2081 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2018 Marvell Semiconductor.
#
# Version Control Information:
#
#  $Id$
#  revision: 0.1
#
#  Author:  YuanMin
#
#  May 20, 2019
#####################################################################################################################
import pytest
from configparser import ConfigParser

def pytest_addoption(parser):
    parser.addoption("--fsname", action="store", default="",
        help="list of fsname at samba server")
    parser.addoption("--case", action="store", default="./testcases",
        help="list of stringinputs to pass to test functions")
    
def get_timeout():
    '''
    get the config file for specific test suite from the global config file.
    config_file: "./iol_cfg.txt", fixed for now in this script - only postcommit for now, avoid such para from PI.
    '''
    config = ConfigParser()
    config.read("iol_cfg.txt")
    timeout = config.get('IOL', "postcommit_iol_timeout")
    
def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    fsname_value = metafunc.config.getoption("fsname")

    if "fsname" in metafunc.fixturenames and fsname_value is not None:
        metafunc.parametrize("fsname", [fsname_value])
    
def pytest_collection_modifyitems(items):
    config = ConfigParser()
    config.read("iol_cfg.txt")
    timeout = config.get('IOL', "postcommit_iol_timeout")
    print("timeout is {}".format(timeout))
    
    for item in items:
        item.add_marker(pytest.mark.timeout(timeout=timeout, method='signal'))

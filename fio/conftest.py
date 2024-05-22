#!/usr/bin/python
import pytest
from configparser import ConfigParser
#only for test_fio
def pytest_addoption(parser):
    parser.addoption(
        "--caseSuite", 
        dest="caseSuite", 
        help="case suite to be executed."
        )

#def get_timeout(config_file, caseSuite):
    #'''
    #get the config file for specific test suite from the global config file.
    #config_file: "./fio_cfg.txt", fixed in this script (at the top)
    #caseSuite: test suite: precommit, postcommit or nightly
    #'''
    #config = ConfigParser()
    #config.read(config_file)
    ##log= config.get("Fio", "log")
    #timeout = config.get('Fio', caseSuite+'_timeout')
    
    #return timeout
#def pytest_collection_modifyitems(config, items):
    #case = config.getoption('caseSuite')
    #timeout = get_timeout('fio_cfg.txt', case)
    #for item in items:
        #item.add_marker(pytest.mark.timeout(timeout=timeout, method='signal'))
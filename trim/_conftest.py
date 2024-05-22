#!/usr/bin/python
import pytest
from configparser import ConfigParser

def pytest_addoption(parser):
    parser.addoption(
        "--lba_count",
        action="store",		
        dest="lba_count",
        required=True,
        help="number of LBA's to be trimmed."
        )

@pytest.fixture(scope='session')
def lba_count(request):
    lba_value = request.config.option.lba_count
    return lba_value

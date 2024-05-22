#!/usr/bin/python
import pytest
from configparser import ConfigParser

def pytest_addoption(parser):
    parser.addoption(
        "--action",
        action="store",		
        dest="action",
        required=True,
        help="number of LBA's to be trimmed."
        )

@pytest.fixture(scope='session')
def action(request):
    action = request.config.option.action
    return action

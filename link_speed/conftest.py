#!/usr/bin/python
import pytest
from configparser import ConfigParser


def pytest_addoption(parser):
    parser.addoption(
        "--caseSuite",
        dest="caseSuite",
        help="case suite to be executed."
    )
    parser.addoption("--interval", action="store", default="60",
                     help="change link speed interval time")
    parser.addoption("--loop", action="store", default="200",
                     help="change link speed loop times")


@pytest.fixture(scope="class")
def get_parameter(request):
    interval = request.config.getoption("interval")
    loop = request.config.getoption("loop")
    return loop, interval
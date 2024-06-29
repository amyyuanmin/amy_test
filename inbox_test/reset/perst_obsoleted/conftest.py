import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--loop", action="store", default="1", help="how many loops will be executed for PMU test"
    )

@pytest.fixture(scope="function")
def loop(request):
    return request.config.getoption("--loop")


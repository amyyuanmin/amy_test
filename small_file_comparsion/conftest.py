from pytest import fixture

def pytest_addoption(parser):
    parser.addoption(
        "--test_loop", 
        action="store", 
        default="10000", 
        help="The counts of the loops for the testing. Default value is 10000 loops"
    )
    parser.addoption(
        "--test_runtime", 
        action="store", 
        default="72", 
        help="The run time for the test(seconds). Default is 72 hours"
    )

    parser.addoption(
        "--device_type", 
        action="store", 
        #default="72", 
        help="The device type is NVMe or SATA."
    )

def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    test_loop_value = metafunc.config.getoption("test_loop")
    test_runtime_value = metafunc.config.getoption("test_runtime")
    device_type_value = metafunc.config.getoption("device_type")

    if "test_loop" in metafunc.fixturenames and test_loop_value is not None:
        metafunc.parametrize("test_loop", [test_loop_value])

    if "test_runtime" in metafunc.fixturenames and test_runtime_value is not None:
        metafunc.parametrize("test_runtime", [test_runtime_value])

    if "device_type" in metafunc.fixturenames and device_type_value is not None:
        metafunc.parametrize("device_type", [device_type_value])

#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2022 Marvell International Ltd. 
# All Rights Reserved.
#
# This file contains information that is confidential and proprietary to Marvell International Ltd. Commercial use of 
# this code is subject to licensing terms and is permitted only on semiconductor devices manufactured by or on behalf 
# of Marvell International Ltd or its affiliates. Distribution subject to written consent from Marvell International Ltd.
#
######################################################################################################################

from _pytest.outcomes import skip
import pytest
import os
from smart_lib import SMART
import logging
import shutil

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')

def find_host():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

@pytest.fixture(scope = "module")
def log_path():
    hostname = find_host()
    log_path = os.path.join(os.path.dirname(__file__), hostname + "_smart_test_logs")
        
    if os.path.exists(log_path):
        shutil.rmtree(log_path)
    os.mkdir(log_path) 
    
    yield log_path
        
@pytest.fixture(scope = "module")
def prepare_device_conf(request, check_device, log_path):
        
    #for runtime log
   LOGGER = logging.getLogger()
   LOGGER.setLevel(logging.INFO)
   FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
   run_log = "smart_log.log"
   handler = logging.FileHandler(run_log)
   handler.setFormatter(FORMATTER)
   LOGGER.addHandler(handler)
   smart = SMART(LOGGER)

   yield smart
   os.system('mv *.log ' + log_path)

@pytest.mark.timeout(timeout = 300, method = "signal")
def test_smart_data_units_read(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('data_units_read', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test data_units_read failed')

@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_data_units_written(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('data_units_written', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test data_units_written failed')

@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_host_read_commands(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('host_read_commands', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test host_read_commands failed')

@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_host_write_commands(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('host_write_commands', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test host_write_commands failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_available_spare(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('available_spare', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test available_spare failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_available_spare_threshold(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('available_spare_threshold', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test available_spare_threshold failed')

@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_percentage_used(prepare_device_conf, size):
    smart = prepare_device_conf
    result = smart.run_smart_data('percentage_used', size) #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test percentage_used failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_power_on_hours(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_power('power_on_hours') #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test power_on_hours failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_power_cycles(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_power('power_cycles') #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test power_cycles failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_unsafe_shutdowns(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_feature('unsafe_shutdowns') #unified function for all smart data checking methods  
    if result != 'Pass':
        pytest.fail('Smart test unsafe_shutdowns failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_critical_warning(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_feature('critical_warning') #unified function for all smart data checking methods    
    if result != 'Pass':
        pytest.fail('Smart test critical_warning failed')
        
@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")    
def test_smart_temperature(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_temperature('temperature') #unified function for all smart data checking methods    
    if result != 'Pass':
        pytest.fail('Smart test temperature failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")
def test_media_error(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_feature('media_errors') #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test media errors failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")
def test_num_err_log_entries(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_feature('num_err_log_entries') #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test num_err_log_entries failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")
def test_warning_temp_time(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_feature('warning_temp_time') #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test warning_temp_time failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")
def test_critical_comp_time(prepare_device_conf):
    smart = prepare_device_conf
    result = smart.run_smart_feature('critical_comp_time') #unified function for all smart data checking methods
    if result != 'Pass':
        pytest.fail('Smart test critical_comp_time failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")
def test_thm_temp_trans_count(prepare_device_conf):
    smart = prepare_device_conf
    result1 = smart.run_smart_feature('thm_temp1_trans_count') #unified function for all smart data checking methods
    result2 = smart.run_smart_feature('thm_temp2_trans_count')
    if result1 != 'Pass' or result2 != 'Pass':
        pytest.fail('Smart test thm_temp_trans_count failed')

@pytest.mark.skip
@pytest.mark.timeout(timeout = 300, method = "signal")
def test_thm_temp_total_time(prepare_device_conf):
    smart = prepare_device_conf
    result1 = smart.run_smart_feature('thm_temp1_total_time') #unified function for all smart data checking methods
    result2 = smart.run_smart_feature('thm_temp2_total_time')
    if result1 != 'Pass' or result2 != 'Pass':
        pytest.fail('Smart test thm_temp_total_time failed')
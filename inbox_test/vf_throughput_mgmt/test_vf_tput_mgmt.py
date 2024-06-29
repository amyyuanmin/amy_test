#!/usr/bin/python
######################################################################################################################
# Copyright (c) 2022 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2022 Marvell Semiconductor.
#
# Version Control Information:
#
#  $Id$
#  revision: 0.1
#
#  Author:  Leon Cheng
#
#  Feb. 17, 2022
#
#####################################################################################################################

import pytest
import logging
import os, shutil
from vf_tput_mgmt_util import VF_Tput_Mgmt

class Test_CCL:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname, rpi_ip, rpi_path):
        global vf_tput_mgmt_result, test_flag, vf_tput_mgmt_util, mapping_table, ns_list
        folder_name = hostname + "_vf_tput_mgmt_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        test_flag = 0
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        vf_tput_mgmt_result = log_folder + '/vf_tput_mgmt_result.log'
        vf_tput_mgmt_util = VF_Tput_Mgmt(rpi_ip, rpi_path)
        
        vf_number_used_for_test = 3
        ns_list = vf_tput_mgmt_util.sriov_ns_preparation(vf_number_used_for_test)
        mapping_table = {1: ["1f", "ff"], 2: ["5f", "1fff"], 3: ["1f00", "ffff"]}
        yield
        logging.info("Recover to default: disable VF throughput management")
        vf_tput_mgmt_util.enable_tput_mgmt() #recover to default
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")
          
    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self):
        '''
        Abort test if test failed
        '''
        global test_flag
        if test_flag == -1: 
            logging.error("Former test failed, abort test")
            pytest.exit("Former test failed, abort test")

    @pytest.mark.timeout(timeout=1000, method="signal")
    def test_vf_tput_mgmt_timer_based(self):
        '''
        3 scenarios:
        1. time based control
        2. fw based control
        3. update Cur_Du by fw
        '''
        fio_log_folder = "vf_tput_mgmt_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        
        vf_tput_mgmt_util.prepare_timer_based_control(mapping_table = mapping_table, timer_hex = "773593fe")
        
        # FIO check defined here
        
    @pytest.mark.timeout(timeout=1000, method="signal")
    def test_vf_tput_mgmt_fw_based(self):
        '''
        3 scenarios:
        1. time based control
        2. fw based control
        3. update Cur_Du by fw
        '''
        fio_log_folder = "vf_tput_mgmt_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)

        vf_tput_mgmt_util.prepare_fw_based_control(mapping_table = mapping_table, mode = 2)
        
        # FIO check defined here
        
    @pytest.mark.timeout(timeout=1000, method="signal")
    def test_vf_tput_mgmt_fw_update_cur_du(self):
        '''
        3 scenarios:
        1. time based control
        2. fw based control
        3. update Cur_Du by fw
        '''
        fio_log_folder = "vf_tput_mgmt_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)

        vf_tput_mgmt_util.prepare_fw_based_control(mapping_table = mapping_table, mode = 3)
        du_mapping = {1: "1ff", 2: "fff", 3: "fff"}
        vf_tput_mgmt_util.set_cur_du(du_mapping = du_mapping)
        # FIO check defined here
        
        
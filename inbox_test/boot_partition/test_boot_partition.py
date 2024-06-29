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
#  Mar. 22, 2022
#
#####################################################################################################################

import pytest
import logging
import os, shutil
from boot_partition_util import Boot_Partition_Util
import sys
sys.path.append("../")
from common import util
import time

class Test_Boot_Partition:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname, controller, scenario):
        global boot_partition_result, bp_util
        folder_name = hostname + "_boot_partition_logs"

        if scenario == "single_pf":
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name)
            os.mkdir(folder_name)
        dmsg_log = "dmesg_{}.log".format(scenario)
        bp_util = Boot_Partition_Util(controller, dmsg_log)
        
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        boot_partition_result = log_folder + '/boot_partition_result.log'
        yield
        os.system("mv *.log {}".format(log_folder))

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request, scenario):
        '''
        Set test result to fail before test, this should be updated after test if test passed
        '''
        global test_result
        if scenario != request.node.name.replace("test_boot_partition_", ""):
            pytest.skip("Skip test for other scenario")
        test_result = "Fail"            
        yield
        # test_name = os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0].lstrip("test_")
        test_name = request.node.name.replace("test_", "")
        with open(boot_partition_result, "a+") as f:
            f.write("{}: failed\n".format(test_name))
    
    @pytest.mark.timeout(timeout=600, method="signal")
    def test_boot_partition_single_pf(self):
        '''
        Read boot partition based on single PF setup
        '''
        global test_result
        logging.info("##########Step0. Prepare customized nvme driver##########")
        bp_util.prepare_driver(wait_flag=False)
        
        logging.info("##########Step1. Check Boot Partition supported##########")
        bp_util.check_bp_supported()
        
        logging.info("##########Step2. Check Boot Partition info, just for record##########")
        bp_util.check_bp_info()
        
        time.sleep(10)  # wait some time to let device ready
        
        logging.info("##########Step3. Read Boot Partition data and check read status, including abnormal scenarios##########")
        bp_util.read_boot_partition("nvme0")
        bp_util.check_bp_read_result()
        test_result = "Pass"
        
    @pytest.mark.timeout(timeout=1200, method="signal")
    def test_boot_partition_multi_pf(self):
        '''
        Read boot partition based on multi PF setup
        '''
        global test_result
        time.sleep(60)
        ns_list = util.check_get_real_ns()
        logging.info("##########Step0. Prepare customized nvme driver##########")
        bp_util.prepare_driver()
        
        logging.info("##########Step1. Check Boot Partition supported##########")
        bp_util.check_bp_supported()
        
        logging.info("##########Step2. Check Boot Partition info, just for record##########")
        bp_util.check_bp_info()
        
        time.sleep(10)
        
        for i in range(0, len(ns_list)):            
            logging.info("##########Step3. Read Boot Partition data and check read status, including abnormal scenarios##########")
            bp_util.read_boot_partition("nvme{}".format(i))
            bp_util.check_bp_read_result()
        test_result = "Pass"
        
    @pytest.mark.timeout(timeout=1200, method="signal")
    def test_boot_partition_sriov(self):
        '''
        Read boot partition based on SRIOV setup
        '''
        global test_result
        bp_util.enable_sriov(32)
        time.sleep(60)
        logging.info("##########Step0. Prepare customized nvme driver##########")
        bp_util.prepare_driver()
        
        logging.info("##########Step1. Check Boot Partition supported##########")
        bp_util.check_bp_supported()
        
        logging.info("##########Step2. Check Boot Partition info, just for record##########")
        bp_util.check_bp_info()
        
        time.sleep(10)
        
        for i in range(0, 33):  # currently 32 VF + 1PF supported
            logging.info("##########Step3. Read Boot Partition data and check read status, including abnormal scenarios##########")
            bp_util.read_boot_partition("nvme{}".format(i))
            bp_util.check_bp_read_result()
        test_result = "Pass"


        
        
        
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

import sys
sys.path.append("../")
from function_check_basic.set_get_feature.set_get_feature_lib import Set_Get_Feature
import pytest
import logging
import time, os, shutil
from sfvs.nvme import nvme

class Test_Write_Cache:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global log_folder
        folder_name = hostname + "_write_cache_logs"

        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
    
    @pytest.mark.timeout(timeout=300,method="signal")
    def test_write_cache(self, feature_id, value_to_set):
        global log_folder
        result_log = log_folder + '/write_cache_result.log'
        result = "Fail"
        info = None
        if value_to_set == '0': 
            info = 'Disable'
        elif value_to_set == '1':
            info = 'Enable'

        if feature_id == '6': 
            feature_id = nvme.FeatureId.VolatileWriteCache

        logging.info('Start test write cache {}'.format(info))
        recover = False
        try:
            test = Set_Get_Feature()
            res = test.set_feature_verify(feature_id, int(value_to_set), recover) 
            if res == 0:
                result = 'Pass'
        except Exception as e:
            logging.error("Initialize failed:{}".format(e))
            
        with open(result_log, "a+") as f:
            f.write("Write_cache: {}\n".format(result))

        if result == "Fail":
            pytest.fail("Write_cache {} failed".format(info))
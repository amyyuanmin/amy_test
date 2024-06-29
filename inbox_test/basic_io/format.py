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

import pytest
import logging
import time, os, shutil
from fvt_adm_cmd_common import fvt_adm

class Test_Format:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, controller, namespace, hostname):
        global log_folder, adm_common
        folder_name = hostname + "_basic_io_logs"

        # TestBed folder has been cleaned up during testbed_cp process, plus need to run test for different lba_size.
        # if os.path.exists(folder_name):
        #     shutil.rmtree(folder_name)
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        adm_common = fvt_adm(controller, namespace)

    @pytest.mark.timeout(timeout=300,method="signal")
    def test_format(self, format_lbaf, project):
        global log_folder, adm_common
        result_log = log_folder + '/format_result.log'
        result = "Fail"
        size_list0 = ['0', '9', '10', '11', '12', '13', '14', '15', '16']
        size_list1 = ['1', '2', '3', '4', '5', '6', '7', '8']
        try:
            if project == 'vail':
                ret = adm_common.format(format_lbaf, 'vail')
            else:
                ret = adm_common.format(format_lbaf)
            time.sleep(5)
            if ret == 0:
                ns_data = adm_common.ns_identify()
                if ns_data != -1:
                    flbas = ns_data.flbas
                    lba_ds = ns_data.lbaf(flbas & 0x0F).ds
                    lba_size = 2 ** lba_ds	
                    logging.info("Identify LBA size is: {}".format(lba_size))
                    
                    lba_size_refer = 0
                    
                    if format_lbaf in size_list0:  # 512 byte LBA
                        lba_size_refer = 512
                    elif format_lbaf in size_list1:
                        lba_size_refer = 4096

                    if lba_size == lba_size_refer:
                        logging.info("Format to {} LBA size successfully".format(lba_size))
                        result = "Pass"
                    else:
                        logging.error("Real lba size: {}, expected: {}".format(lba_size, lba_size_refer))
                        result = "Fail"
                    
                    if str(flbas) == str(format_lbaf):
                        logging.info("Format to flbas:{} successfully".format(flbas))
                    else:
                        logging.error("Real flbas: {}, expected: {}".format(flbas, format_lbaf))
                        result = "Fail"
                        
        except Exception as e:
            logging.error("Initialize failed:{}".format(e))
            
        with open(result_log, "a+") as f:
            f.write("Format: {}\n".format(result))

        if result == "Fail":
            pytest.fail("Format failed")
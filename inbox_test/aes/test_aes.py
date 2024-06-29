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
#  Mar. 9, 2022
#
#####################################################################################################################

import pytest
import logging
import time
import os, shutil
from .aes_util import AES_Util
from common import util

class Test_AES:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname, rpi_ip, rpi_path):
        global aes_result, aes_util
        folder_name = hostname + "_aes_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        aes_result = log_folder + '/aes_result.log'
        aes_util = AES_Util(rpi_ip, rpi_path)
        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.mark.single_ns_aes
    @pytest.mark.timeout(timeout=3600, method="signal")
    def test_aes(self):
        '''
        Check if AES encryption successfully
        '''
        fio_log_folder = "aes_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        lbafs = ["4", "11"]  # For AES, only 4 and 11 supported

        q_depth_list = [32, 128]
        bs_list = ["4k", "128k", "256k", "1024k"]
        
        size_each_int = int(100 / (len(q_depth_list) * len(bs_list))) 
        size_each = str(size_each_int) + "%"
        
        for lbaf in lbafs:
            logging.info("########AES test on LBAF: {}#########".format(lbaf))
            index = 0
            util.nvme_format(lbaf, ses=1)   
            # aes_util.uart_enable_aes(hex(int(lbaf)).strip("0x"))  # AES enabled by default when format 
            for q_depth in q_depth_list:
                for bs in bs_list:
                    offset = str(index * size_each_int) + "%"
                    logging.info("########Basic IO check with QD: {}, BS: {}#########".format(q_depth, bs))
                    logging.info("Issue write to drive, offset={}, size={}".format(offset, size_each))
                    aes_util.fio_runner(io_type="write", size=size_each, offset=offset, q_depth=q_depth, bs=bs, thread=1, log_folder=fio_log_folder, timeout=120)
                    time.sleep(5)
                    logging.info("Read out written data and do compare")
                    aes_util.fio_runner(io_type="read", size=size_each, offset=offset, q_depth=q_depth, bs=bs, thread=4, log_folder=fio_log_folder, timeout=120)
                    index += 1
            if lbafs.index(lbaf) == 0:
                logging.info("Disable interrupt to let host received encrypted data, otherwise 6C error reported and no data respond to host")
                aes_util.uart_disable_interrupt()
            logging.info("########AES encryption check#########")
            aes_util.uart_disable_aes(lbaf)
            logging.info("Read out some of written data and do compare, should met mismatch")
            aes_util.fio_runner(io_type="read", size="10m", offset=offset, q_depth=q_depth, bs=bs, thread=4, log_folder=fio_log_folder, expected_failure="verify type mismatch", timeout=60, log_str="aes_check_lbaf_{}.log".format(lbaf))
    
    @pytest.mark.multi_ns_aes
    @pytest.mark.timeout(timeout=3600, method="signal")
    def test_multi_ns_aes(self):
        '''
        Check if AES encryption successfully
        '''
        fio_log_folder = "aes_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        lbafs = ["4", "11"]  # For AES, only 4 and 11 supported

        q_depth_list = [32, 128]
        bs_list = ["4k", "128k", "1024k"]
        
        size_each_int = int(100 / (len(q_depth_list) * len(bs_list))) 
        size_each = str(size_each_int) + "%"
        try:
            for lbaf in lbafs:
                ns_num = 4  # 4 NS for testing
                logging.info("########AES test on LBAF: {}#########".format(lbaf))
                aes_util.prepare_multiple_ns(ns_num, lbaf)
                ns_list = util.check_get_real_ns()
                for ns in ns_list:
                    logging.info("########AES test on NS: {}#########".format(ns))
                    index = 0
                    for q_depth in q_depth_list:
                        for bs in bs_list:
                            offset = str(index * size_each_int) + "%"
                            logging.info("########Basic IO check with QD: {}, BS: {}#########".format(q_depth, bs))
                            logging.info("Issue write to drive, offset={}, size={}".format(offset, size_each))
                            aes_util.fio_runner(ns_str=ns, io_type="write", size=size_each, offset=offset, q_depth=q_depth, bs=bs, thread=1, log_folder=fio_log_folder, timeout=120)
                            time.sleep(5)
                            logging.info("Read out written data and do compare")
                            aes_util.fio_runner(ns_str=ns, io_type="read", size=size_each, offset=offset, q_depth=q_depth, bs=bs, thread=4, log_folder=fio_log_folder, timeout=120)
                            index += 1
                if lbafs.index(lbaf) == 0:
                    logging.info("Disable interrupt to let host received encrypted data, otherwise 6C error reported and no data respond to host")
                    aes_util.uart_disable_interrupt()
                logging.info("########AES encryption check#########")
                aes_util.uart_disable_aes(lbaf)
                logging.info("Read out some of written data and do compare, should met mismatch")
                aes_util.fio_runner(io_type="read", size="100m", offset=offset, q_depth=q_depth, bs=bs, thread=4, log_folder=fio_log_folder, expected_failure="84", timeout=60)
                aes_util.clear_env(ns_num) 
        except Exception as e:
            pass    
        finally:  # finally is just used to let this always happen
            aes_util.clear_env(ns_num, expect_fail=True)  
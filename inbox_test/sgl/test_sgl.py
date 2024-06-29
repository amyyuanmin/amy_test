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
#	Test Case Name : Scatter Gather List 
#	Test Case Description : Verify Scatter Gather List Data Transfer.
#	Step1: Check Identify if SGL is supported, and check io status.
#####################################################################################################################

import pytest
import logging
import os,shutil
import sys
sys.path.append("..")
from common import util
import time

class Test_SGL:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global sgl_result
        folder_name = hostname + "_sgl_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        sgl_result = log_folder + '/sgl_result.log'

        yield
        files = os.listdir(os.getcwd())
        for item in files:
            if '.log' in item :
                os.system('sudo mv {} {}'.format(item,folder_name))
    
    @pytest.mark.timeout(timeout=100, method="signal")
    def test_sgl(self,nvme0):
        global result
        ctrl, ns = nvme0

        # check sgl is supported on dut. sgls bit 2 should be set to 1.
        id_data = ctrl.identify_specific_cns(cns=1)
        logging.info('0x%08x'%(id_data.sgls)) 
        if id_data.sgls & 0x2 == 0:
            logging.error('identify check: sgl is not supported')
            pytest.fail('sgl is not supported')
        
        # run io with io range:4M, io size from 4k to 256k.
        offset = [0, "32m", "64m", "96m", "128m", "160m", "192m"]
        bs = ["4k", "8k", "16k","32k","64k","128k","256k"]
        for i in range(7):
            logging.info('start write and read with bs = {}, offset = {}'.format(bs[i],offset[i]))
            util.fio_runner(io_type="write", size="32m", bs=bs[i], offset=offset[i], pattern="0x11bb11bb", time_based = 0, log_str="sgl_enabled_write_bs_{}.log".format(bs[i]))
            time.sleep(5)
            util.fio_runner(io_type="randread", size="32m", bs=bs[i], offset=offset[i], pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_{}.log".format(bs[i]))
        # util.fio_runner(io_type="write", size="32m", bs="256k", offset='32m', pattern="0x11bb11bb", time_based = 0, log_str="sgl_enabled_write_bs_256k.log")
        # time.sleep(5)
        # util.fio_runner(io_type="randread", size="32m", bs="4k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_4k.log")
        # util.fio_runner(io_type="randread", size="32m", bs="8k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_8k.log")
        # util.fio_runner(io_type="randread", size="32m", bs="16k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_16k.log")
        # util.fio_runner(io_type="randread", size="32m", bs="32k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_32k.log")
        # util.fio_runner(io_type="randread", size="32m", bs="64k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_64k.log")
        # util.fio_runner(io_type="randread", size="32m", bs="128k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_128k.log")
        # util.fio_runner(io_type="randread", size="32m", bs="256k", offset=0, pattern="0x11bb11bb", runtime = 30, log_str="sgl_enabled_read_bs_256k.log")
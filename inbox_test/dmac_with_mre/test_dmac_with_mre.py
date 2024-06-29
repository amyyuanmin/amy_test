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
#  May. 13, 2022
#
#####################################################################################################################

import pytest
import logging
import random
import os, shutil
import time
from dmac_util import Dmac_Util
import sys
sys.path.append("../")
from common import util

class Test_DMAC:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname, rpi_ip, rpi_path, fw_log_indicator):
        global dmac_util, dmac_result
        folder_name = hostname + "_dmac_with_mre_logs"

        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        dmac_result = log_folder + '/dmac_with_mre_result.log'
        dmac_util = Dmac_Util(rpi_ip, rpi_path, fw_log_indicator)
        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.mark.timeout(timeout=100, method="signal")
    def test_dmac(self, lbaf, buffer_addr):
        '''
        lbaf: currently for SDK, LBAF 4 and 11 is designed for encryption
        Test flow: Flash fw: LBAF4 -> BLOCK mode test -> queue mode test -> reflash fw -> LBAF 11 -> BLOCK mode test -> queue mode test
        For normal DMAC(without T10)Use different LBA for fill and copy, and different pattern for block and queue mode.
        For T10, since pattern are all 0 to follow design purpose and only fill implemented, use different LBA for block and queue mode.
        '''
        fio_log_folder = "dmac_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        
        lba_size_mapping = {"4": 4096, "8": 4096, "11": 512, "13": 512}  # 8/13 for T10 information generation and validation
        lba_size = lba_size_mapping[lbaf]
        start_lba = hex(random.randint(0, 10000)) # it's hex value, but cannot be start with 0x in UART cmd
        
        lba_list = {}  # dict used for easy scale out, for ex, if one more mode added
        test_mode = ["block", "queue"] # block first
        test_category = ["fill", "copy"]
        lba_num_each_category = 4096 // lba_size  # We use fio to check data, for FIO the min io size is 4K, so for lba size lower than 4k, i.e. 512 byte, 8 lba should be operated for test
        for category in test_category:
            tmp_lba_list = []
            for i in range(0, lba_num_each_category):
                tmp_lba_list.append(hex(int(start_lba, 16) + test_category.index(category) * lba_num_each_category + i).lstrip("0x"))
            lba_list[category] = tmp_lba_list
        logging.info("LBA list used for test: {}".format(lba_list))
        
        offset_list = {}  # offset used in FIO corresponding to test LBA        
        for category in test_category: # for lba size 512 byte, 8 lba corresponds to a offset and size=4k
            offset_list[category] = int(lba_list[category][0], 16) * lba_size
            
        data_size_mapping = {"4": "1000", "11": "200", "13": "200", "8": "1000"}   # 1000 refer 4096 bytes, while 200 for 512 bytes
        total_size_mapping = {"4": "1018", "11": "218", "13": "220", "8": "1028"} 
        # size in total during copy action
        # Lba format 4 : data size = 4096 bytes,  bcrc enabled size = 4 bytes, hlba enabled size = 8 bytes, mpecc enabled size = 12 bytes.
        # whole data size =    data size  +  bcrc size + hlba size + mpecc size = 4096 + 4 + 8 +12 =  4120 = 0x1018 
        # For T10:
        # Lba format 8 : data size = 4096 bytes,  meta size = 16 bcrc enabled size = 4 bytes, hlba enabled size = 8 bytes, mpecc enabled size = 12 bytes.
        #  whole data size =   meta size + data size  +  bcrc size + hlba size + mpecc size = 16 + 4096 + 4 + 8 +12 =  4136 = 0x1028 
        
        buffer_addr_1 = dmac_util.uart_util.alloc_buffer(total_size_mapping[lbaf])
        buffer_addr_2 = dmac_util.uart_util.alloc_buffer(total_size_mapping[lbaf])
        
        logging.info("##########Start test of DMAC Engine with MRE, at LBAF {}##########S".format(lbaf))
        logging.info("##########Step1. NVMe format to lbaf: {}##########".format(lbaf))
        pi = 0  # Protection Information
        if lbaf == "8" or lbaf == "13":
            pi = 1
        util.nvme_format(lbaf, ses=1, pi=pi)
        
        if lbaf == "4" or lbaf == "11":
            logging.info("##########Step2. Check data on host before test, all data should be 0##########")
        elif lbaf == "8" or lbaf == "13": 
            logging.info("##########Step2. Prefill data on host before test and do validation - for T10 related tests##########")
        for category, offset in offset_list.items():
            if lbaf == "8" or lbaf == "13":
                # T10 is used to encrypt 0, so prefill non-zero data as precondition
                util.fio_runner(io_type="write", size='4k', bs='4k', offset=offset, pattern="0x55aa", q_depth=1, time_based=0, log_folder=fio_log_folder, log_str="check_before_lbaf_{}_enc_{}_write.log".format(lbaf, category))
                time.sleep(5)  # to let FTL flush
                util.fio_runner(io_type="read", size='4k', bs='4k', offset=offset, pattern="0x55aa", q_depth=1, time_based=0, log_folder=fio_log_folder, log_str="check_before_lbaf_{}_enc_{}_read.log".format(lbaf, category))
            elif lbaf == "4" or lbaf == "11":
                util.fio_runner(io_type="read", size="4k", bs="4k", offset=offset, pattern="0x0000", q_depth=1, time_based=0, log_folder=fio_log_folder, log_str="check_before_lbaf_{}_enc_{}.log".format(lbaf, category))
        
        pattern_mapping = {"block": "0xaaaaaaaa", "queue": "0xbbbbbbbb"}  # use different pattern for test, for UART, 0x is not allowed, but for fio, 0x is a MUST
        for mode in test_mode:
            logging.info("##########LoopStep3. Test in {} mode##########".format(mode))
            logging.info("##########LoopStep3.1. Encrypted fill##########")
            for lba in lba_list["fill"]:
                if lbaf == "4" or lbaf == "11":
                    dmac_util.enc_fill(mode=mode, buffer_addr=buffer_addr_1, pattern=pattern_mapping[mode].lstrip("0x"), size=data_size_mapping[lbaf], hlba=lba)
                elif lbaf == "8" or lbaf == "13":
                    # for T10, as design purpose, should test with filling with 0
                    # as workaround, use different LBA list for block and queue fill
                    if mode == "queue":
                        lba = lba_list["copy"][lba_list["fill"].index(lba)]
                    dmac_util.t10_enc_fill(mode=mode, buffer_addr=buffer_addr_1, pattern="0", size=data_size_mapping[lbaf], hlba=lba, apptag="ABCD", reftag_lsb=lba, lbaf=lbaf)
                dst_addr = hex(int(buffer_addr, 16) + int(total_size_mapping[lbaf], 16) * int(lba, 16)).lstrip("0x")
                dmac_util.uart_util.mem_copy(src_addr=buffer_addr_1, dst_addr=dst_addr, size=total_size_mapping[lbaf])
            logging.info("##########LoopStep3.2. Check data on host after test##########")  
            if lbaf == "4" or lbaf == "11":
                util.fio_runner(io_type="read", size="4k", bs="4k", offset=offset_list["fill"], time_based=0 , pattern=pattern_mapping[mode], q_depth=1, log_folder=fio_log_folder, log_str="check_after_lbaf_{}_enc_fill.log".format(lbaf))
            elif lbaf == "8" or lbaf == "13":
                # for T10, as design purpose, should test with filling with 0
                # as workaround, use different LBA for block and queue fill
                if mode == "block":
                    util.fio_runner(io_type="read", size="4k", bs="4k", offset=offset_list["fill"], time_based=0, pattern="0x0000", q_depth=1, log_folder=fio_log_folder, log_str="check_after_lbaf_{}_block_enc_fill.log".format(lbaf))
                elif mode == "queue":
                    util.fio_runner(io_type="read", size="4k", bs="4k", offset=offset_list["copy"], time_based=0, pattern="0x0000", q_depth=1, log_folder=fio_log_folder, log_str="check_after_lbaf_{}_queue_enc_fill.log".format(lbaf,))
            if lbaf == "4" or lbaf == "11":
                logging.info("##########LoopStep3.3. Encrypted copy##########")
                for lba in lba_list["copy"]:
                    if mode == "block":
                        dmac_util.uart_util.mem_set(buffer_addr=buffer_addr_1, pattern=pattern_mapping[mode].lstrip("0x"), size=data_size_mapping[lbaf])
                    elif mode == "queue":
                        dmac_util.uart_util.xorfill(buffer_addr=buffer_addr_1, pattern=pattern_mapping[mode].lstrip("0x"), size=data_size_mapping[lbaf])
                    dmac_util.enc_copy(mode=mode, src_addr=buffer_addr_1, dst_addr=buffer_addr_2, size=data_size_mapping[lbaf], hlba=lba)
                    dst_addr = hex(int(buffer_addr, 16) + int(total_size_mapping[lbaf], 16) * int(lba, 16)).lstrip("0x")
                    dmac_util.uart_util.mem_copy(src_addr=buffer_addr_2, dst_addr=dst_addr, size=total_size_mapping[lbaf])
                logging.info("##########LoopStep3.4. Check data on host after test##########")    
                util.fio_runner(io_type="read", size="4k", bs="4k", offset=offset_list["copy"], time_based=0, pattern=pattern_mapping[mode], q_depth=1, log_folder=fio_log_folder, log_str="check_after_lbaf_{}_enc_copy.log".format(lbaf, offset))
        
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
#  Feb. 5, 2022
#
#####################################################################################################################

import pytest
import logging
import os, shutil
from common import util
from .ccl_util import CCL_Util
from itertools import product

class Test_CCL:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname, rpi_ip, rpi_path, fw_log_indicator):
        global ccl_result, ccl_util
        folder_name = hostname + "_consistent_completion_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        ccl_result = log_folder + '/consistent_completion_result.log'
        ccl_util = CCL_Util(rpi_ip, rpi_path, fw_log_indicator)
        yield
        logging.info("Recover consistent completion latency to default")
        ccl_util.uart_ccl("0") #recover to default
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.mark.timeout(timeout=100, method="signal")
    def test_ccl(self, build):
        '''
        latency: configured consistent completion latency, in ms
        1. Get actual latency without CCL configured, this should not exceeds 1ms(can be configured)
        2. Set CCL to 0, latency value should be similar to no CCL configured.
        3. Set CCL at different latency(can be configured) and check with different IO cfg.
        '''
        fio_log_folder = "ccl_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        latency_cfg = ccl_util.parse_config("latency")
        qd = ccl_util.parse_config("qd")
        bs = ccl_util.parse_config("bs")
        thread = list(ccl_util.parse_config("thread"))
        latency_ref = int(ccl_util.parse_config("latency_ref"))
        runtime = int(ccl_util.parse_config("runtime"))
        
        for latency in latency_cfg:
            if build == "Ramdrive":
                size = "100%"
                offset = '0'
            elif build == "E2e":
                size_int = int(100 / (len(qd) * len(bs) * len(thread)))
                size = str(size_int) + "%" 
            time_based = {"E2e_write": 0, "E2e_read": 1, "Ramdrive_write": 1, "Ramdrive_read": 1}
            fio_log = None
            latency_ref_real_write = 0 #real latency without consistent completion latency configured
            latency_ref_real_read = 0 #real latency without consistent completion latency configured
            # UART Format from the 2nd latency setting
            if latency_cfg.index(latency) != 0 and build == "E2e":
                # ccl_util.uart_util.uart_format()
                util.nvme_format(format_lbaf = "1")  # nvme format now really format the drive
            latency = int(latency) * 1000
            latency_hex = hex(latency).lstrip("0x")  #latency is in us, uart cmd requires no 0x as prefix, otherwise, latency 0 configured.
            if latency == 0:
                logging.info("#########Test under consistent completion configured to 0, not cover all io cfg#########")
                for io_type in ["write", "read"]:
                    fio_log = ccl_util.fio_runner(size=size, io_type=io_type, runtime=runtime, time_based=time_based[build + "_" + io_type], log_folder=fio_log_folder)
                    if io_type == "write":
                        latency_ref_real_write = ccl_util.util.get_latency(fio_log)
                    elif io_type == "read":
                        latency_ref_real_read = ccl_util.util.get_latency(fio_log)
                    if latency_ref_real_write > latency_ref * 1000 or latency_ref_real_read > latency_ref * 1000:
                        pytest.fail("Initial latency is too big, larger than {}ms".format(latency_ref))

                ccl_util.uart_ccl("0")
                if build == "E2e":
                    offset = size
                ccl_util.fio_runner(io_type="write", size=size, offset=offset, runtime=runtime, time_based=time_based[build + "_write"], log_folder=fio_log_folder, expect_latency=latency_ref_real_write)
                ccl_util.fio_runner(io_type="read", size=size, offset=offset, runtime=runtime, time_based=time_based[build + "_read"], log_folder=fio_log_folder, expect_latency=latency_ref_real_read)

            else:
                logging.info("#########Test under consistent completion configured to {}us#########".format(latency))
                ccl_util.uart_ccl(latency_hex)
                count = 0
                comb = product(qd, bs, thread)
                for condition in comb:
                    logging.info("#########QD:{}, IO SIZE:{}, Thread:{}#########".format(condition[0], condition[1], condition[2]))
                    if build == "E2e":
                        offset = str(size_int * count) + "%"
                    for io_type in ["write", "read"]:
                        runtime_tmp = runtime
                        if io_type == "write":
                            runtime_tmp = runtime + 10  #ten more time to ensure more data written than read out
                        # if int(condition[1].strip("k")) > 128 and io_type == "write":
                        #     continue
                        ccl_util.fio_runner(io_type=io_type, size=size, offset=offset, \
                            q_depth=condition[0], bs=condition[1], thread=condition[2], \
                                runtime=runtime_tmp, time_based=time_based[build + "_" + io_type], log_folder=fio_log_folder, expect_latency=latency)
                    count = count + 1    
                
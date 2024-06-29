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
#  Feb. 7, 2022
#
#####################################################################################################################

import logging
import os
from configparser import RawConfigParser
from common import util
from common.uart_util import UART_Util
import pytest

class CCL_Util():
    def __init__(self, rpi_ip, rpi_path, fw_log_indicator):
        self.uart_util = UART_Util(rpi_ip, rpi_path, fw_log_indicator)
        self.config_file = "./ccl_cfg.txt"

    def parse_config(self, item):
        config = RawConfigParser()
        config.read(self.config_file)

        item_value = config.get('Consistent Completion', item).strip()
        if "," in item_value:
            item_value = item_value.split(",")

        return item_value

    def fio_runner(self, ns_str = "/dev/nvme0n1", io_type ="write", size = "100%", 
                   bs = "128k", offset = 0, q_depth = 32, thread = 1, 
                   runtime = 0, time_based = 1, expect_latency = 0,
                   log_folder = os.getcwd(), timeout = 0):
        '''
        Start a fio process
        io_type: for ex. sequential write(write), sequential read(read), random write(randwrite), random read(randread)
        size: size of IO
        bs: io size of each write
        log_folder: where the fio log stored, for record and result analysis
        timeout: timeout for if IO still running check
        runtime: runtime argument for fio
        expect_latency: expected latency, if not 0, check this
        time_based: if time_based, always run specified runtime, otherwise, will stop either IO finished on SIZE or runtime
        '''
        log_str = "{}_{}_{}_{}_{}x{}_{}.log".format(io_type, offset, size, bs, q_depth, thread, expect_latency)
        
        if timeout == 0:
            timeout = int(self.parse_config("timeout"))
            
        log_str = util.fio_runner(ns_str=ns_str, io_type=io_type, size=size, bs=bs, offset=offset, \
            q_depth=q_depth, thread=thread, runtime=runtime, time_based=time_based, timeout=timeout, \
                log_folder=log_folder, log_str=log_str)

        if expect_latency != 0:
            allowed_delta = float(self.parse_config("allowed_delta"))
            latency_real = util.get_latency(log_str)
            delta = (abs(latency_real - expect_latency)) / expect_latency
            if delta > allowed_delta:
                logging.error("Expected latency: {} v.s. real latency: {}, delta: {} > {}".format(expect_latency, latency_real, delta, allowed_delta))
                pytest.fail("Expected latency: {} v.s. real latency: {}, delta: {} > {}".format(expect_latency, latency_real, delta, allowed_delta))
            else:
                logging.info("Expected latency: {} v.s. real latency: {}, test passed".format(expect_latency, latency_real))
        else:
            return log_str
    
    def uart_ccl(self, latency_hex):
        '''
        Send UART cmd to change consistent completion latency
        latency_hex: argument for UART cmd, it's HEX value(string) and in ms
        '''
        logging.info("Set Consistent Completion Latency to: {}us".format(int(latency_hex, 16)))
        self.uart_util.send_uart_cmd("concmpl {}".format(latency_hex), "[CmdConsistentCmplTest] gConsistentCmplThreshold = {} us".format(int(latency_hex, 16)))

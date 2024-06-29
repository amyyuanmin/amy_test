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

import logging
import pytest
import os
from common import util
from common.uart_util import UART_Util

class AES_Util():
    def __init__(self, rpi_ip, rpi_path):
        self.uart_util = UART_Util(rpi_ip, rpi_path)

    def fio_runner(self, ns_str = "/dev/nvme0n1", io_type ="write", size = "100%", 
                   bs = "128k", offset = 0, q_depth = 32, thread = 1, 
                   runtime = 0, time_based = 0,
                   log_folder = os.getcwd(), timeout = 0, expected_failure = None, log_str = None):
        '''
        Start a fio process
        io_type: for ex. sequential write(write), sequential read(read), random write(randwrite), random read(randread)
        size: size of IO
        bs: io size of each write
        log_folder: where the fio log stored, for record and result analysis
        timeout: timeout for if IO still running check
        runtime: runtime argument for fio
        time_based: if time_based, always run specified runtime, otherwise, will stop either IO finished on SIZE or runtime
        expected_failure: for some scenario that expect specified error, for ex. AES test expect mismatch(err=84) error after read out encrypted data
        '''
        if log_str == None:
            if expected_failure == None:
                log_str = "{}_{}_{}_{}_{}x{}.log".format(io_type, offset, size, bs, q_depth, thread)
            else:
                log_str = "{}_{}_{}_{}_{}x{}_expect_err_{}.log".format(io_type, offset, size, bs, q_depth, thread, expected_failure)
        
        log_str = util.fio_runner(ns_str=ns_str, io_type=io_type, size=size, bs=bs, offset=offset, \
            q_depth=q_depth, thread=thread, runtime=runtime, time_based=time_based, timeout=timeout, \
                log_folder=log_folder, log_str=log_str, expected_failure=expected_failure)

        return log_str
    
    def uart_enable_aes(self, lbaf):
        '''
        Send UART cmd to enable AES
        Obsoleted, AES enbled with nvme format
        '''
        logging.info("Enable AES")
        self.uart_util.send_uart_cmd("AES 1 {}".format(lbaf), end_keyword="HostAdmin_ProcessMonitorCmd 1 AES: On")

    def uart_disable_aes(self, lbaf):
        '''
        Send UART cmd to disable AES
        '''
        logging.info("Disable AES")
        lbaf_hex = hex(int(lbaf)).strip("0x")  # Value in UART cmd is in HEX
        self.uart_util.send_uart_cmd("AES 0 {}".format(lbaf_hex), end_keyword="EnableAes:off lbaf:{}. OK!!  errorCode:0".format(lbaf))
        
    def uart_disable_interrupt(self):
        '''
        Disable interrupt to let host received encrypted data
        Otherwise drive will interrupt the mismatched data to host
        '''
        self.uart_util.send_uart_cmd("wmem 15011014 11ff")
        
    def uart_enable_interrupt(self):
        '''
        Enable interrupt for futher normal testing
        '''
        self.uart_util.send_uart_cmd("wmem 15011014 0")
        
    def prepare_multiple_ns(self, ns_num, lbaf):
        '''
        For AES testing on multiple NS(Single PF), SRIOV/Multi-PF not covered
        ns_num: how many NS will be created
        lbaf: the LBAF spcified when create NS
        '''
        logging.info("Create multiple NS for testing")
        for i in range(0, ns_num):
            create_cmd = "sudo nvme create-ns /dev/nvme0 -s 0x100000 -c 0x100000 -f {} -m 0".format(lbaf)
            attach_cmd = "sudo nvme attach-ns /dev/nvme0 -n {} -c 0".format(i+1)
            if util.execute_cmd(create_cmd) != 0 or util.execute_cmd(attach_cmd) != 0:
                pytest.fail("Prepare multiple NS failed")
        rescan_cmd = "sudo nvme ns-rescan /dev/nvme0"
        util.execute_cmd(rescan_cmd)
        
    def clear_env(self, ns_num, expect_fail = False):
        '''
        Clear NS created for test
        the ns_num should be the same as created
        '''
        logging.info("Clear env at last")
        for i in range(ns_num, 0, -1):
            detach_cmd = "nvme detach-ns /dev/nvme0 -n {} -c 0".format(i)
            delete_cmd = "nvme delete-ns /dev/nvme0 -n {}".format(i)
            util.execute_cmd(detach_cmd, expect_fail=expect_fail)
            util.execute_cmd(delete_cmd, expect_fail=expect_fail)
    
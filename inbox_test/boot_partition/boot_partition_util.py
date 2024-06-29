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
import os, time
import sys
sys.path.append("../")
from common import util
        
class Boot_Partition_Util():
    def __init__(self, ctrl, dmsg_log):
        self.ctrl = ctrl
        self.dmesg_log = dmsg_log

    def __parse_reg_value(self, reg_value, bit_range):
        '''
        Get required bits values of a Register symbol
        reg_val: value of the specified register symbol
        bit_range: for ex, 14:0 - from 0 bit to 14 bit
        return: int
        '''
        bit_upper = int(bit_range.split(":")[0])
        bit_lower = int(bit_range.split(":")[1])
        if bit_lower == 0:
            specified_reg_value = bin(reg_value).lstrip("0b").zfill(64)[-(bit_upper+1):]
        else:
            specified_reg_value = bin(reg_value).lstrip("0b").zfill(64)[-(bit_upper+1):-bit_lower]
        return int(specified_reg_value, 2)
        
    def check_bp_supported(self):
        '''
        Read CTRL.CAP to check if Boot Partition if supported or not
        '''
        _, BPINFO = self.ctrl.get_reg(0x0, 8)
        bp_supported = self.__parse_reg_value(BPINFO, "45:45")
        logging.info("Boot Partition supported: {}".format(bp_supported))
        
        if bp_supported != 1:
            logging.error("Boot Partition not supported")
            pytest.fail("Boot Partition not supported")
            
    def check_bp_info(self):
        '''
        Check BP information(BPID and BPSIZE) for read preparation
        '''
        _, BPINFO = self.ctrl.get_reg(0x40, 4)
        bp_size = self.__parse_reg_value(BPINFO, "14:0")
        logging.info("BP size is: {} x 128k".format(bp_size))
        bp_id = self.__parse_reg_value(BPINFO, "31:31")
        logging.info("BP ID is: {}".format(bp_id))
        return bp_id, bp_size
    
    def read_boot_partition(self, controller):
        '''
        Read boot partition via new nvme driver
        Controller: read boot partition from which controller
        '''
        cmd = "sudo nvme admin-passthru /dev/{} -o 0xC0".format(controller)
        _, out = util.execute_cmd(cmd, timeout = 30, out_flag = True)
        if "Admin Command Vendor Specific is Success and result: 0x00000000" not in out[0]:
            logging.error("Test executed failed")
            pytest.fail("Test executed failed")

        ret2 = util.execute_cmd("dmesg > {}".format(self.dmesg_log))
        
        if ret2 != 0:
            logging.error("Log collect failed")
            pytest.fail("Log collect failed")     
        
    def check_bp_read_result(self):
        '''
        Check test result via dmesg log
        '''
        with open(self.dmesg_log, "r") as f:
            lines = f.readlines()
            for line in lines:
                logging.debug(line)
            
            for line in lines:
                if "Test failed" in line:
                    logging.error("Some test failed, pleaes check dmesg log")
                    pytest.fail("Some test failed, please check dmesg log")
        
        logging.info("All test passed")
    
    def prepare_driver(self, wait_flag = True):
        '''
        Replace nvme driver with the specified with test code. 
        wait_flag: for some scenario, for ex. SRIOV, it requires some time to let fw ready
        '''
        _, out = util.execute_cmd("sudo uname -a", out_flag = True)
        supported_kernel = ["4.15", "5.8", "5.13"]
        driver_folder = ""
        for kernel in supported_kernel:
            if kernel in out[0]:
                driver_folder = "driver_" + kernel
                break
        else:
            logging.warning("Not support this kernel")
            pytest.fail("Not support this kernel")
        # cur_dir = os.path.split(os.path.realpath(__file__))[0] 
        os.chdir(driver_folder)
        _, out = util.execute_cmd("sudo rmmod nvme", timeout = 60, out_flag = True)
        # ret=0
        # out:['rmmod: ERROR: Module nvme is in use'], no idea why error with status 0, use output to check
        if out == []:
            _, out = util.execute_cmd("sudo rmmod nvme_core", timeout = 60, out_flag = True) # the filename is nvme-core.ko, but the module name is nvme_core
            if wait_flag:
                time.sleep(60)
            if out == []:
                _ = util.execute_cmd("sudo insmod nvme-core.ko", out_flag = True)
                if out == []:
                    _ = util.execute_cmd("sudo insmod nvme.ko", out_flag = True)
                    if wait_flag:
                        time.sleep(60)
        
        util.execute_cmd("sudo dmesg -c")  # clear dmesg log
        os.chdir(os.getcwd())
        if out != []:
            logging.error("Prepare customized driver failed: {}, abort test".format(out))
            pytest.exit("Prepare customized driver failed, abort test")
            
    def enable_sriov(self, vf_amount):
        '''
        Enable SRIOV with 32 VF
        Timeout to 10 seconds
        '''
        max_vf_amount = 32
        pci_addr = util.get_pci_addr_list()[0] # there should be only one nvme ctrl during this test
        logging.info("Enable SRIOV with {} VFs".format(vf_amount))
        sriov_cmd = "echo {} > /sys/bus/pci/devices/{}/sriov_numvfs".format(vf_amount, pci_addr)
        if vf_amount > max_vf_amount:
            result = util.execute_cmd(sriov_cmd, 10, expect_fail = True, expect_err_info = "Numerical result out of range")
        else:
            result = util.execute_cmd(sriov_cmd, 10)
        
        logging.info("Result of enable sriov: {}".format(result))
        
        return result
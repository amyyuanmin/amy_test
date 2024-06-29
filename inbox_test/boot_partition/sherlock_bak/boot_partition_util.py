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
from sfvs.nvme.utils import Utils
import time
# from sfvs.pci.pci_device import PCIDevice
# from sfvs.pci.pciutilis import PCIUtilis
        
class Boot_Partition_Util():
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.data = None

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
        Read PCI.CAP to check if Boot Partition if supported or not
        '''
        # pciUtilis = PCIUtilis()
        # dev = PCIDevice(3, 0, 0, pciUtilis)
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
    
    def write_to_read_boot_partition(self, bp_id, bp_size):
        '''
        Write to register BPRSEL to read boot partition
        '''
        bp_size_byte = bp_size * 128 * 1024 
        logging.info("Allocate memory buffer for boot partition read")
        self.data = Utils.allocate_memory(bp_size_byte)
        addr = self.data.__array_interface__['data'][0]
        logging.info(hex(addr))
        logging.info("Set BPMBL.BMBBA to the physical address")
        self.ctrl.set_reg(0x48, addr, 8)
        
        bp_size = bp_size * 128 // 4  # bp size in BPRSEL is multiple of 4k
        read_offset = 0x0
        # combine upper value to a whole value for 0x44
        # 
        logging.info("Set BPRSEL.BPRSZ to {} x 4k, BPID to {}, BPROF to {}".format(bp_size, bp_id, read_offset))
        self.ctrl.set_reg(0x44, bp_size, 4)
        
    def check_bp_read_result(self, expect_fail = False):
        '''
        Check if read boot partition successfully via read register BPINFO.BRS
        00b No Boot Partition read operation requested
        01b Boot Partition read in progress
        10b Boot Partition read completed successfully
        11b Error completing Boot Partition read
        '''
        _, BPINFO = self.ctrl.get_reg(0x40, 4)
        status = self.__parse_reg_value(BPINFO, "25:24")
        logging.info("BPINFO: {}".format(BPINFO))
        while status == 1:
            logging.info("Reading boot partition")
            time.sleep(1)
            _, BPINFO = self.ctrl.get_reg(0x40, 4)
            status = self.__parse_reg_value(BPINFO, "25:24")
        if not expect_fail:
            if status == 2:
                logging.info("Read successfully")
                logging.info("Read boot partition data: {}".format(self.data))
            elif status == 3:
                logging.error("Read boot partition failed")
                pytest.fail("Read boot partition failed")
        else:
            if status == 2:
                logging.error("Read boot partition successfully, but should be failed")
                pytest.fail("Read boot partition successfully, but should be failed")
            elif status == 3:
                logging.info("Read boot partition failed as expected")
        if status == 0:
            logging.warning("Read status not pass or fail")
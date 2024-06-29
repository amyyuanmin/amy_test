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
#  Feb. 17, 2022
#
#####################################################################################################################

import logging
import os
from configparser import RawConfigParser
from ..common import util
from ..common.uart_util import UART_Util
import pytest

class VF_Tput_Mgmt():
    def __init__(self, rpi_ip, rpi_path):
        self.config_file = "./vf_tput_cfg.txt"
        self.uart_util = UART_Util(rpi_ip, rpi_path)

    def __parse_config(self, item):
        config = RawConfigParser()
        config.read(self.config_file)

        item_value = config.get('VF Tput Mgmt', item).strip()
        if "," in item_value:
            item_value = item_value.split(",")

        return item_value

    def fio_runner(self, ns_str = "/dev/nvme0n1", io_type ="write", size = "100%", 
                    bs = "128k", offset = 0, q_depth = 32, thread = 1, 
                    runtime = 0, time_based = 1,
                    log_folder = os.getcwd(), timeout = 0):
        '''
        Start a fio process
        io_type: for ex. sequential write(write), sequential read(read), random write(randwrite), random read(randread)
        size: size of IO
        bs: io size of each write
        log_folder: where the fio log stored, for record and result analysis
        timeout: timeout for if IO still running check
        runtime: runtime argument for fio
        time_based: if time_based, always run specified runtime, otherwise, will stop either IO finished on SIZE or runtime
        '''
        log_str = "{}_{}_{}_{}_{}x{}.log".format(io_type, offset, size, bs, q_depth, thread)
        
        if timeout == 0:
            timeout = int(self.__parse_config("timeout"))
            
        log_str = util.fio_runner(ns_str=ns_str, io_type=io_type, size=size, bs=bs, offset=offset, \
            q_depth=q_depth, thread=thread, runtime=runtime, time_based=time_based, timeout=timeout, \
                log_folder=log_folder, log_str=log_str)

        return log_str
    
    def __enable_tput_mgmt(self):
        '''
        Enable VF throughput management
        '''
        logging.info("Enable VF throughput management")
        
        self.uart_util.send_uart_cmd("VFTHRUQARBEN 1", "Enable Qarb throughtput management")
    
    def disable_tput_mgmt(self):
        '''
        Disable VF throughput management
        '''
        logging.info("Disable VF throughput management")
        
        self.uart_util.send_uart_cmd("VFTHRUQARBEN 0", "Disable Qarb throughtput management")
        
    def __set_du_weight(self, data_unit = "4k", read_weight = 2, write_weight = 2):
        '''
        Set the data unit size and write weight, read weight.
        Data Unit Size: 0:512B, 3:4KB. Default: 4KB
        Weighting factor to be multiplied by the command data size for a read I/O command, when the current data unit is being updated
        '''
        logging.info("Set data unit size to {}, write weight: {}, read weight: {}".format(data_unit, write_weight, read_weight))
        if data_unit == "4k":
            data_unit = 3
        elif data_unit == "512b":
            data_unit = 0
        self.uart_util.send_uart_cmd("VFTHRUSETDUWIGHT {} {} {}".format(data_unit, read_weight, write_weight), "Data Unit {} read weight {} write weight {}".foramt(data_unit, read_weight, write_weight))

    def __set_vf_mapping_table(self, func_id, min_du, max_du):
        '''
        Set max data unit and min data unit for specified function
        func_id: 1 based index for VF
        '''
        logging.info("Set min_du:{}, max_du:{} for VF:{}".format(min_du, max_du, func_id))
        self.uart_util.send_uart_cmd("VFTHRUFILLFIDTBL {} {} {}".format(func_id, min_du, max_du), "funId {}, minDu {} maxDu {}".format(func_id, int(min_du, 16), int(max_du, 16)))
        
    def __fill_pf_mapping_table(self):
        '''
        Set max data unit and min data unit for physical function
        As required, for PF, the max value need to be set.
        '''
        logging.info("Fill mapping table for PF, the max allowed value should be configured for PF")
        self.uart_util.send_uart_cmd("VFTHRUFILLFIDTBL 0 1fffff 1fffff", "funId 0, minDu 2097151 maxDu 2097151")
        
    def __set_control_mode(self, mode):
        '''
        Set VF Tput mgmt mode
        1(0x1): Timer based
        2(0x2): Firmware control based
        3(0x3): Update Cur_Du by firmware
        '''
        out_dict = {1: "Timer based control", 2: "FW based control", 3: "FW update data unit"}
        logging.info("Set management mode to {}".format(out_dict[mode]))
        self.uart_util.send_uart_cmd("VFTHRUMODE {}".format(mode), out_dict[mode])
    
    def set_cur_du(self, du_mapping):
        '''
        set Cur_Du for scenario update Cur_Du by fw
        du_mapping: {vf_id1: cur_du1, vf_id2: cur_du2}
        '''
        for vf_id, du_value in du_mapping.items():
            self.uart_util.send_uart_cmd("VFTHRUSETCURDU {} {}".format(vf_id, du_value), "funId {} curDu {}".format(vf_id, int(du_value, 16)))
        
    def __set_control_timer(self, timer_hex):
        '''
        Set control timer for timer based control, from fw: timer unit of the value need to be confirmed with ASIC team
        '''
        logging.info("Set timer to: {}".format(int(timer_hex, 16)))
        self.uart_util.send_uart_cmd("VFTHRUSETTIMER {}".format(timer_hex), "Set internal time {}".format(int(timer_hex, 16)))
    
    def kick_off_new_session(self):
        '''
        Kick off a new VF session from Firmware, if it's not timer based control
        By this, Cur_Du will be updated by minus Max_Du
        '''
        logging.info("Kick off a new VF session")
        self.uart_util.send_uart_cmd("VFTHRUSTART", "Start VF througput mgr")
    
    def __basic_flow(self, du_weigh_cfg, mappint_table):
        '''
        Common flow for VF tput mgmt test
        mappint_table: format {vf_id_1: [min_du_1, max_du_1], vf_id_2: [min_du_2, max_du_2]}
        '''
        self.__enable_tput_mgmt()
        self.__set_du_weight(data_unit = du_weigh_cfg["data_unit"], read_weight = du_weigh_cfg["read_weight"], write_weight = du_weigh_cfg["write_weight"])
        self.__fill_pf_mapping_table()
        for vf_id, du_values in mappint_table.items():
            self.__set_vf_mapping_table(vf_id, du_values[0], du_values[1])        
        
    def prepare_timer_based_control(self, du_weigh_cfg = {"data_unit": "4k", "read_weight": 2, "write_weight": 2}, mapping_table = None, timer_hex = None):
        '''
        UART configure preparation for timer based control step by step
        '''
        self.__basic_flow(du_weigh_cfg, mapping_table)
        self.__set_control_mode(1)
        self.__set_control_timer(timer_hex)
    
    def prepare_fw_based_control(self, du_weigh_cfg = {"data_unit": "4k", "read_weight": 2, "write_weight": 2}, mapping_table = None, mode = 2):
        '''
        UART configure preparation for fw based control(including update Cur_Du by fw) step by step
        mode: 2(0x2): Firmware control based
        3(0x3): Update Cur_Du by firmware
        '''
        self.__basic_flow(du_weigh_cfg, mapping_table)
        self.__set_control_mode(mode)
        
    ###################################################
    #Below for SRIOV/NS MGMT related
    ###################################################
    def __get_pci_addr_list(self):
        '''
        Get pci addr of the nvme device
        '''
        cmd = "lspci -D | grep 'Non-Volatile memory' | grep 'Marvell' | grep -o '....:..:....'"
        ret, pci_addr_list = util.execute_cmd(cmd, 10, out_flag = True)
        logging.info("PCI addr list: {}".format(pci_addr_list))
        return pci_addr_list

    def __enable_check_sriov(self, vf_amount):
        '''
        Enable SRIOV with #vf_amount VF, if vf_amount=0 means disable all VF
        Timeout to 10 seconds
        '''
        max_vf_amount = 32
        pci_addr = self.__get_pci_addr_list()[0] # there should be only one nvme ctrl during this test
        logging.info("Enable SRIOV with {} VFs".format(vf_amount))
        sriov_cmd = "echo {} > /sys/bus/pci/devices/{}/sriov_numvfs".format(vf_amount, pci_addr)
        if vf_amount > max_vf_amount:
            result = util.execute_cmd(sriov_cmd, 10, expect_fail = True, expect_err_info = "Numerical result out of range")
        else:
            result = util.execute_cmd(sriov_cmd, 10)
        logging.info("Result of enable sriov: {}".format(result))
        if result != 0:
            pytest.fail("Enable SRIOV failed")
        # Check if expected VF enabled
        # return 0 on success
        # real amount or -1 on fail
        pci_addr_list = self.__get_pci_addr_list()
        real_amount = len(pci_addr_list)
        result = 0
        if real_amount == 0:
            logging.error("No controllers found")
            result = -1
        elif real_amount != (vf_amount + 1):
            if vf_amount > max_vf_amount: 
                if real_amount == 1:
                    logging.info("Got 1 controller which is as expected")
                    result = 0
                else:
                    logging.warning("There might be controllers enabled before, just warning")
            else:
                logging.error("Found {} controllers, expected: {}".format(real_amount, vf_amount + 1))
                result = real_amount
        else:
            if vf_amount > max_vf_amount: 
                logging.error("VF amount exceeds max.")
            else:
                logging.info("Expected {} controllers found".format(real_amount))
        if result != 0:
            pytest.fail("Check SRIOV failed")

    def __check_get_real_ns():
        '''
        check if NS really detected after attach and get the real NS name if detected
        Issue: The ctrl id and the real number in controllers might not be the same
        (for ex, id is 21, the controller might show as /dev/nvme20, doubtful, need to check with a third party drive)
        Return: all detected NS list
        '''
        ns_list = []
        list_cmd = "nvme list | grep nvme"
        ret, out = util.execute_cmd(list_cmd, 120, out_flag = True)
        # out ex: ['/dev/nvme0n1     S41FNX0M117868       SAMSUNG MZVLB256HAHQ-000L2               1         256.06  GB / 256.06  GB    512   B +  0 B   0L1QEXD7']
        if out == []:
            logging.warning("No NS found")
        else:
            for item in out:
                ns = item.split(" ")[0].strip()
                ns_list.append(ns)
        logging.info("Detected NS list: {}".format(ns_list))

        return ns_list

    def sriov_ns_preparation(self, vf_amount):
        '''
        Multi namespace setup before VF tput mgmt testing
        '''
        self.__enable_check_sriov(32) # enable max VF, no need to use each of them for test
        for func_id in range(0, vf_amount):
            create_cmd = "sudo nvme create-ns /dev/nvme{} -s 0x1600000 -c 0x1600000 -f 0 -m 0".format(func_id)
            attach_cmd = "sudo nvme attach-ns /dev/nvme0 -n {} -c {}".format(func_id + 1, func_id)
            scan_cmd = "sudo nvme ns-rescan /dev/nvme{}".format(func_id)
            if util.execute_cmd(create_cmd) == 0 and util.execute_cmd(attach_cmd) == 0 and util.execute_cmd(scan_cmd) == 0:
                logging.info("NS on nvme{} created and attached successfully".format(func_id))
            else:
                logging.error("NS on nvme{} created and attached failed".format(func_id))
                pytest.fail("NS on nvme{} created and attached failed".format(func_id))

        ns_list = self.__check_get_real_ns()
        return ns_list
    
    def identify_check(self, ns_block_list):
        '''
        For admin cmd block check
        Currently HAL Exerciser use Round Robin Arbitration as default, if Cur_Du > Max_Du, admin should also be blocked
        '''
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

import time
from sfvs.nvme import nvme
import configparser
from sfvs.nvme.controller import ShnValue
import subprocess
import os

class cGSD_func:
    def __init__(self, logger):
        self.logging = logger
        self.SSH_CMD = "sudo sshpass -p 123456 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"


    def shutdown(self, ctrl):
        try:
            wait_cnt = 0
            with ctrl as c:
                self.logging.info("send shutdown notification")
                ret = c.gsd_assert(ShnValue.NORMAL_SHUTDOWN_NOTIFICATION)
                time.sleep(15)

        except nvme.NVMeException as e:
            pass

    def loadINI(self):
        curpath = os.path.dirname(os.path.realpath(__file__))
        cfgpath = os.path.join(curpath, 'gsd_cfg.ini')
        conf = configparser.ConfigParser()
        conf.read(cfgpath, encoding='utf-8')
        return conf
        
        
    def compare_ptn(self, lba_idx, src_ptn, dst_ptn):
        BYTE_LEN = 8
        BYTE_mask = [0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x80]
        result_str = ""
        for ptn_idx in range(len(src_ptn)):
            result_byte = src_ptn[ptn_idx]^dst_ptn[ptn_idx]
            for byte_idx in range(BYTE_LEN):
                if BYTE_mask[byte_idx] & result_byte:
                    result_str+=("LBA idx:%d Byte idx:%d bit idx:%d 0x%x <-> 0x%x\n" % (lba_idx, ptn_idx, byte_idx, src_ptn[ptn_idx],dst_ptn[ptn_idx]))
        return result_str
    
    def cal_compare_data(self, slba, t1_list, t2_list):
        summary = ""
        folder_name = "miscompare"
        if os.path.exists(folder_name):
            os.remove(folder_name)
        os.makedirs(folder_name)

        for i in range(int(len(t1_list)/512)):
            file_name1 = "SLBA%d_LBA%d_Fail_Data_Dump.bin" % (slba, i)
            file_name2 = "SLBA%d_LBA%d_Expect_Data_Dump.bin" % (slba, i)
            with open(folder_name+"/"+file_name1, "wb") as f:
                f.write(t1_list[512*i:512*(i+1)])
            with open(folder_name+"/"+file_name2, "wb") as f:
                f.write(t2_list[512*i:512*(i+1)])
            summary+=self.compare_ptn(i, t1_list[512*i:512*(i+1)], t2_list[512*i:512*(i+1)])

        with open(folder_name+"/summary.txt", "w") as f:
            f.write(summary)    
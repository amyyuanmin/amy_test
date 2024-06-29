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

#################################################################################
# drive area
    def drive_power_off(self, ip):
        self.power_init(ip)
        self.device_remove()
        self.power_setting(ip, "off")
        time.sleep(1)

    def device_remove(self):
        list_Marvell_device_cmd = "sudo lspci | grep Marvell"
        cmd1 = list_Marvell_device_cmd
        result = os.popen(cmd1)
        out = result.read().strip()
        result.close()
        pci_num = out.strip()[0:7]
        pci_number = "0000:" + pci_num
        self.logging.debug(pci_number)
        cd_mode_pci_device_remove = " sudo chmod 777 /sys/bus/pci/devices/" + pci_number + "/remove"
        remove_pci_device = " sudo echo 1 >/sys/bus/pci/devices/" + pci_number + "/remove"
        cmd2 = cd_mode_pci_device_remove
        cmd3 = remove_pci_device

        p = subprocess.Popen(cmd2, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)

        self.logging.info("Device had been removed")
        result = 0
        p = subprocess.Popen(cmd3, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        t_beginning = time.time()
        seconds_passed = 0
        while True:
            if p.poll() is not None:
                break
            time.sleep(1)
            seconds_passed = time.time() - t_beginning
            if seconds_passed > 10:
                # wait for 10 seconds
                p.terminate()
                self.logging.info('No response for remove in 10 seconds, abort')
                result = -1
        p.stdout.close()
        return result

    def device_rescan(self):
        self.logging.info("NVMe rescan")
        cmd1 = "sudo chmod 777 /sys/bus/pci/rescan"
        cmd2 = "sudo echo 1 > /sys/bus/pci/rescan"
        p = subprocess.Popen(cmd1, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        result = 0
        p = subprocess.Popen(cmd2, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        t_beginning = time.time()
        seconds_passed = 0
        while True:
            if p.poll() is not None:
                break
            time.sleep(1)
            seconds_passed = time.time() - t_beginning
            if seconds_passed > 10:
                #wait for 10 seconds
                p.terminate()
                self.logging.info('No response for rescan in 10 seconds, abort')
                result = -1
        p.stdout.close()
        return result

    def power_init(self, ip):
        general_cmd = self.SSH_CMD + " " + "pi" + "@" + ip
        self.logging.info("set gpio on")
        cmd1 = general_cmd+" \"echo 37 > /sys/class/gpio/export\""
        cmd2 = general_cmd+" \"echo out > /sys/class/gpio/gpio37/direction\""
        subprocess.Popen(cmd1, shell=True, stdout=subprocess.PIPE)
        time.sleep(1)
        subprocess.Popen(cmd2, shell=True, stdout=subprocess.PIPE)
        time.sleep(1)

    def power_setting(self, ip, power="on"):
        general_cmd = self.SSH_CMD + " " + "pi" + "@" + ip

        if power == "on":
            cmd3 = general_cmd+" \"echo 0 > /sys/class/gpio/gpio37/value\""
        else:
            cmd3 = general_cmd+" \"echo 1 > /sys/class/gpio/gpio37/value\""

        subprocess.Popen(cmd3, shell=True, stdout=subprocess.PIPE)
        time.sleep(1)

    ########################################################################################################
    #simics area
    def send_command2simics(self, simics_cmd, ctrl):
        try:
            self.logging.info("send simics command :" + simics_cmd)
            time.sleep(3)
            with ctrl as c:
                c.send_simics_cmd(simics_cmd)
                self.logging.info(simics_cmd)
        except:
            self.logging.error("send command to simics except")
    ########################################################################################################



    def shutdown(self, ctrl):
        try:
            wait_cnt = 0
            with ctrl as c:
                self.logging.info("send shutdown notification")
                ret = c.gsd_assert(ShnValue.NORMAL_SHUTDOWN_NOTIFICATION)
                time.sleep(10)

        except nvme.NVMeException as e:
            pass

    def drive_gsd(self, ctrl):
        self.shutdown(ctrl)
        self.power_off()




    def reboot_drive(self, ctrl, sim=True):
        print("shutdown")
        self.shutdown(ctrl)
        if sim==True:
            self.send_command2simics("sdssoc.kill-power", ctrl)
            self.logging.info("kill-power")
            time.sleep(300)
            self.logging.info("300")
        else:
            self.power_on_off()


    def create_dat_file_by_LBA(self, pattern, nlb=0, file_name='write_file.bin', byte_per_lba=0):
        pattern = pattern%256
        data_to_write = bytearray()
        nlb+=1 # nlb 0 = 1 lba
        for data_idx in range(nlb):
            for lba_ptn in range (byte_per_lba):
                data_to_write.append(pattern)

            data_idx = data_idx + byte_per_lba
            pattern+=1
            pattern = pattern % 256
        if file_name != '':
           with open(file_name, "wb") as data_file:
                data_file.write(data_to_write)

        return bytes(data_to_write)

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
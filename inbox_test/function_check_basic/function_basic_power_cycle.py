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

from sfvs.nvme import nvme
from sfvs.nvme.controller import ShnValue
from base_func import cGSD_func
import pytest
import configparser
import time
import sys
import os
import logging
import numpy as np
import random
import subprocess
import pickle
from nvme_protocol_test.smart_lib import SMART

np.set_printoptions(threshold=np.inf)
SSH_CMD = "sudo sshpass -p 123456 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
TESTBED_PATH = "/home/fte/FTE/USECASE/Vega_CI_Script/TestBed"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
host = nvme.Host.enumerate()[0]
ctrl = host.controller.enumerate()[0]
ns = ctrl.enumerate_namespace()[0]
smart = SMART(ctrl, ns)


class Test_Power_Cycle():
    def test_power_cycle_basic(self, file_name = 'power_cycle.bin'):
        try:
            list_file = TESTBED_PATH + "/blackbox_tests/function_check_basic/function_check_test_list.bin"
            if not os.path.exists(list_file):
                self.random_write_and_shutdown(list_file)
            else:
                data_read = None
                value = smart.all_smart_data('power_cycles')
                logging.info("power cycle value:{}".format(value))

                #return data_write
                if file_name != '':
                    with open(file_name, 'w') as data:
                        data_write = data.write(str(value))
                else:
                    with open(file_name, 'r') as data:
                        data_read = data.read()
                        #compare_data = compare.append(data_read)
                        logging.info("power cycle:{}".format(data_read))
                        if value == 1 + data_read:
                            logging.info("Check Power cycle successful")
                        else:
                            pytest.fail("Check Power cycle failed")
                            if value == 1 + data_read:
                                logging.info("Check Power cycle successful")
                            else:
                                pytest.fail("Check Power cycle failed")
                os.remove(file_name)                
                self.reboot_and_compare(list_file)
                self.random_write_and_shutdown(list_file)
        
        except nvme.NVMeException as e:
            logging.error('test_power_cycle failed: {}'.format(e))

    def create_tag_pattern_by_tag(self, pattern='random', nlb=0, file_name='write_file.bin', byte_per_lba=0):
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

    def run_smart_power_cycles():
        #value = smart.all_smart_data('power_cycles')
        value_before = smart.all_smart_data('power_cycles')
        logging.info('power_cycles before value: {}'.format(value_before))
        
        value_after = smart.all_smart_data('power_cycles')
        logging.info('power_cycles after value: {}'.format(value_after))
        #logging.info('power_cycles value: {}'.format(value))        
        if value > 4 or value < 0:
            result =  'FAILED'
        else:
            result =  'PASSED'
        return result

    def random_write_loop(self, ns):
        setting_conf=self.loadINI()
        min_assert_cycle = int(setting_conf['basic']['min_assert_cycle'])
        max_assert_cycle = int(setting_conf['basic']['max_assert_cycle'])
        min_nlb = int(setting_conf['basic']['minnlb'])
        max_nlb = int(setting_conf['basic']['maxnlb'])
        rw_lba_list=[]
        logging.debug("rw_loop")
        write_file = 'write_test' + '.bin'

        lbacycle = 1000000

        assert_cycle = random.randint(min_assert_cycle,max_assert_cycle)

        for i in range(int(lbacycle)):
            number_of_lba=random.randint(min_nlb,max_nlb)
            start_lba=random.randint(1, 10000)

            rw_lba_list.append([start_lba,number_of_lba])
            data_write = self.create_tag_pattern_by_tag(pattern=start_lba, nlb=number_of_lba, file_name=write_file, byte_per_lba=512)
            try:
                with ns as n:
                    # write
                    ret, latency = n.write(slba=start_lba, nlb=number_of_lba, data=write_file)
            except nvme.NVMeException as e:
                print('Error: {0} for slba {1}'.format(str(e), start_lba))
                logging.error('Error: {0} for slba {1}'.format(str(e), start_lba))
            msg="index: "+str(i)+" Write Start LBA:"+str(start_lba)+" number_of_lba:"+str(number_of_lba)
            if ret!=0:
                msg += "[Fail]"
            logging.info(msg)

            if i==int(assert_cycle):
                logging.info("random cycle assert")
                return rw_lba_list

    def compare_data(self, base_obj, ns, rw_lba_list):
        logging.debug("rw_loop")
        write_file = 'write_test' + '.bin'
        read_file = 'read_test' + '.bin'
        for i in range(len(rw_lba_list)):
            start_lba=int(rw_lba_list[i][0])
            number_of_lba=int(rw_lba_list[i][1])
            data_size = 512 * (number_of_lba+1)
            data_write = self.create_tag_pattern_by_tag(pattern=start_lba, nlb=number_of_lba, file_name=write_file, byte_per_lba=512)

            try:
                with ns as n:
                    # write
                    ret, latency, dat, mdat = n.read(slba=start_lba, nlb=number_of_lba, data_size=data_size, data_file=read_file)
            except nvme.NVMeException as e:
                print('Error: {0} for slba {1}'.format(str(e), start_lba))
                logging.error('Error: {0} for slba {1}'.format(str(e), start_lba))
            ret = np.array_equal(np.frombuffer(data_write, dtype=np.uint8), dat)
            if not ret:        
                self.miscompare_log_handle(i, len(rw_lba_list), start_lba, number_of_lba, dat, data_write, base_obj)

        return True

    def miscompare_log_handle(self, cmd_idx, cmd_list_len, start_lba, number_of_lba, dat, data_write, base_obj):
        msg="Command index : "+str(cmd_idx) + "/"+  str(cmd_list_len)  + " miscompare at Start LBA:"+str(start_lba)+" nlb:"+str(number_of_lba)            
        logging.info(dat)
        logging.info(np.frombuffer(data_write, dtype=np.uint8))
        print(msg)
        print("Fail Data Dump:")
        print(dat)
        print("Expect Data Pattern:")
        print(np.frombuffer(data_write, dtype=np.uint8))
        base_obj.cal_compare_data(start_lba, dat, np.frombuffer(data_write, dtype=np.uint8))
        print("miscompare_log_handle done")


    def init_handle(self):
        try:
            host = nvme.Host.enumerate()[0]
            ctrl = host.controller.enumerate()[0]
            ns = ctrl.enumerate_namespace()[0]
            base_obj = cGSD_func(logging)
            return ctrl, ns, base_obj
        except Exception as e:
            logging.error('init_handle failed: {}'.format(e))

    def load_list(self, list_file):
        with open (list_file, 'rb') as temp:
            items = pickle.load(temp)
        return list(items)


    def save_list(self, list_file, lba_list):
        with open(list_file, 'wb') as temp:
            pickle.dump(lba_list, temp)

    def random_write_and_shutdown(self, list_file):
        try:
            print("random_write")
            logging.info("-------------random_write Start-------------")
            ctrl, ns, base_obj = self.init_handle()
            rw_lba_list=self.random_write_loop(ns)
            self.save_list(list_file, rw_lba_list)
            logging.info("send nvme shutdown notification")
            base_obj.shutdown(ctrl)
            logging.info("-------------random_write Done-------------")
        except Exception as e:
            print("shutrandom_write fail")
            logging.error('random_write failed: {}'.format(e))



    def reboot_and_compare(self, list_file):
        try:
            print("reboot_and_compare")
            logging.info("-------------reboot_and_compare Start-------------")
            ctrl, ns, base_obj = self.init_handle()
            rw_lba_list = self.load_list(list_file)
            os.remove(list_file)
            self.compare_data(base_obj, ns, rw_lba_list)
            logging.info("-------------reboot_and_compare Done-------------")
        except Exception as e:
            print("reboot_and_compare fail")
            logging.error('reboot_and_compare failed: {}'.format(e))

    def loadINI(self):
        curpath = os.path.dirname(os.path.realpath(__file__))
        cfgpath = os.path.join(curpath, 'gsd_cfg.ini')
        conf = configparser.ConfigParser()
        conf.read(cfgpath, encoding='utf-8')
        return conf
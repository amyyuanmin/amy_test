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

import logging
from sfvs.nvme import nvme
from sfvs.nvme.utils import Utils as utils
import time
import os
import configparser
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

#step1: check oncs bit value to check DSM support
def check_deallocate_loop(lba_size, id_cns1_ns0, result_file, test_common):
    try:
        current_dir = os.path.split(os.path.realpath(__file__))[0]  # get current folder
        run_tests = os.listdir(current_dir)
        filename = "filename"
        for cfg_name in run_tests:
            if "nvme_protocol_cfg.ini" in cfg_name:
                logging.info("Test cfg filename {}".format(cfg_name))
                filename = os.path.join(current_dir, cfg_name)
        config = configparser.ConfigParser()
        config.read(filename)
        write_file = 'write_test_.bin'
        read_file = 'read_test_.bin'
        results_dict = {}
        finalResult = []
        dsm_attribute_bit=int(config['DSM_Default']['attribute_bit'])
        loop_min=int(config['DSM_TC_Deallocate_Time_loop']['loop_time'])
        start_time=time.time()
        test_timeout=start_time+loop_min*60
        slba=int(config['DSM_TC_Deallocate_Time_loop']['SLBA'])#starting LBA
        pattern1=int(config['DSM_Default']['Pattern1'])  #First pattern to write
        w_loop_res_flag=True
        r_loop_res_flag =True
        r2_loop_res_flag = True
        d_loop_res_flag =True
        data_length=int(config['DSM_TC_Deallocate_Time_loop']['Data_length'])*1024 #data length in bytes [kb*1024 [KB should be <= 128]]
        nlb = (data_length // (lba_size) - 1)
        loop_progress = 1
    except Exception as e:
        logging.error("Failed to get parameters from ini file with an error {}".format(str(e)))
    logging.info("Step1: Check ONCS bit value to check DSM support")
    try:
# converting received oncs bit value into binary to check last 3rd bit is one
         res ="{0:b}".format(int(id_cns1_ns0.oncs))
         if res[-3]=="1":
            logging.info("ONCS value is 1 data set management is supported on device")
            results_dict["Data_set_management_support_check:"] = "Passed"
            finalResult.append(0)
         else:
            logging.error("Step1:ONCS value is 0 data set management is supported on device")
            results_dict["Data_set_management_support_check:"] = "Failed"
            finalResult.append(1)
    except Exception as e :
        logging.error("Step1:ONCS value check failed {}".format(str(e)))
        results_dict["Data_set_management_support_check:"] = "Failed"
        finalResult.append(1)

    logging.info("Write-read-deallocate loop over sane range of LBA")
    logging.info("Step2:Write -read and deallocation check for pattern {} for {}min is in progress".format(pattern1,loop_min))
    try:
        while time.time() < test_timeout:
#showing loop progress of the operation:
            if ((test_timeout - time.time()) // 60) == ((((test_timeout - start_time) // 60) / 100) * (100 - loop_progress * 10)):
                logging.info("Loop run time is {}% completed".format(loop_progress * 10))
                loop_progress = loop_progress + 1

# step2:write known pattern over range of LBA
            try:
                seed, data_write = utils.create_dat_file(data_size=data_length, file_name=write_file, pattern=pattern1)
                w_ret=test_common.io_common.nvme_write_test(slba,nlb, data_write)
                if w_ret !=0:
                    w_loop_res_flag=False
            except Exception as e:
                w_loop_res_flag = False

# step3:Executing a read command to read a known data pattern written in step 2.
            try:
                r_ret,data =test_common.io_common.nvme_read_test(slba,nlb,data_length, read_file)
                check_read_data = list(set(data))
                if len(data) != data_length or len(check_read_data) != 1 or check_read_data[0] != pattern1:
                    r_loop_res_flag=False
            except Exception as e:
                r_loop_res_flag = False

#step4:Executing Dataset Management command with the Attribute – Deallocate (AD) field set to ‘True' for same range of LBA.
            try:
                d_nlb=data_length//(lba_size)
                d_ret=test_common.adm_common.deallocate([[dsm_attribute_bit,d_nlb,slba]])
                if d_ret != 0:
                    d_loop_res_flag=False
            except Exception as e:
                d_loop_res_flag = False

# step5:Executing a read command to read and check if deallocation of range of LBA is successful.
        try:
            r_ret, data = test_common.io_common.nvme_read_test(slba, nlb, data_length, read_file)
            check_deallocation = list(set(data))
            if len(data) != data_length or len(check_deallocation) != 1 or check_deallocation[0] != 0:
                r2_loop_res_flag = False
        except Exception as e:
            r_loop_res_flag=False

    except Exception as e:
        logging.error("Failed to run timeout loop due to error {}".format(str(e)))

    if w_loop_res_flag==True:
        logging.info("Write command executed successfully")
        results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Passed"
        finalResult.append(0)
    else:
        logging.error("Write command execution failed")
        results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Failed"
        finalResult.append(1)

    if r_loop_res_flag ==True :
        logging.info("Read command executed successfully")
        results_dict["Reading_known_pattern_{}:".format(pattern1)] = "Passed"
        finalResult.append(0)
    else:
        logging.error("Read command execution failed")
        results_dict["Reading_known_pattern_{}:".format(pattern1)] = "Failed"
        finalResult.append(1)

    if d_loop_res_flag==True:
        logging.info("Deallocate command executed Successfully")
        results_dict["Deallocation_command_execution:"] = "Passed"
        finalResult.append(0)
    else:
        logging.error("Deallocate command execution failed")
        results_dict["Deallocation_command_execution:"] = "Failed"
        finalResult.append(1)

    if r2_loop_res_flag == True:
        logging.info("Read command execution and Deallocation check")
        results_dict["Read_command_execution_and_Deallocation_check:"] = "Passed"
        finalResult.append(0)
    else:
        logging.error("Read command execution and Deallocation check")
        results_dict["Read_command_execution_and_Deallocation_check:"] = "Failed"
        finalResult.append(1)

    with open(result_file, 'a+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count+=1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')

        if 1 in finalResult:
            logging.error("TC-1 IOL (Test 2.2 : Case 11) - Deallocation in loop for same range of LBA : Failed")
            f.write("\nTC-1 IOL (Test 2.2 : Case 11) - Deallocation in loop for same range of LBA : FAILED\n")
            return -1
        else:
            logging.info("TC-1 IOL (Test 2.2 : Case 11) - Deallocation in loop for same range of LBA: PASSED")
            f.write("\nTC-1 IOL (Test 2.2 : Case 11) - Deallocation in loop for same range of LBA: PASSED\n")
        f.close()

def main(test_common, result_file):
    ns_data = test_common.adm_common.ns_identify()
    flbas = ns_data.flbas
    lba_ds = ns_data.lbaf(flbas & 0x0F).ds
    lba_size = 2 ** lba_ds
    logging.info("\n ")
    logging.info("###############################################################################")
    logging.info("#               TC-1 IOL (Test 2.2 : Case 11) -Deallocation in Loop           #")
    logging.info("###############################################################################")
    id_cns1_ns0 = test_common.adm_common.ns_identify_cns_values(0, 1)
    check_deallocate_loop(lba_size, id_cns1_ns0, result_file, test_common)

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
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
import configparser
import os

def check_deallocate(lba_size, id_cns1_ns0, result_file, test_common):
#reading nvme_protocol.ini file for the parameters
    try:
        current_dir = os.path.split(os.path.realpath(__file__))[0]  # get current folder
        run_tests = os.listdir(current_dir)
        filename="filename"
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
        slba=int(config['DSM_TC_Deallocate']['SLBA']) #starting LBA
        pattern1=int(config['DSM_Default']['Pattern1']) #First pattern to write
        pattern2=int(config['DSM_Default']['Pattern2']) #second pattern to write
        data_length=int(config['DSM_TC_Deallocate']['Data_length'])*1024 #data length in bytes [kb*1024 [KB should be <= 128]]
        nlb = (data_length // (lba_size) - 1)
    except Exception as e:
        logging.error("Failed to get parameters from ini file with an error {}".format(str(e)))

# Step1: check oncs bit value to check DSM support
    logging.info("Step1: Check oncs bit value to check DSM support")
    try:
# Converting received oncs bit value into binary to check last 3rd bit is one
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

# Step2:Executing a Write command to write a known data pattern to the controller.
    logging.info("Step2: Writing first pattern {} over same rang of LBA ".format(pattern1))
    try:
        seed, data_write = utils.create_dat_file(data_size=data_length, file_name=write_file, pattern=pattern1)
        w_ret = test_common.io_common.nvme_write_test(slba,nlb,data_write)
        if w_ret==0:
            logging.info("Write command executed successfully")
            results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Passed"
            finalResult.append(0)
        else:
            logging.error("Write command execution Failed")
            results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("Write command execution Failed with error {}".format(str(e)))
        results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Failed"
        finalResult.append(1)

# Step3:Executing a read command to read a known data pattern written in step 2.
    logging.info("Step2: reading first pattern {} from same rang of LBA ".format(pattern1))
    try:
        r_ret,data =test_common.io_common.nvme_read_test(slba,nlb,data_length, read_file)
        check_read_data = list(set(data))
        if r_ret==0 and len(data) == data_length and len(check_read_data) == 1 and check_read_data[0] == pattern1:
            logging.info("Read command execution and written data check passed")
            results_dict["Read_command_execution_and_written_data_for_pattern:_{}:".format(pattern1)] = "Passed"
            finalResult.append(0)
            logging.info("Data written over LBA's")
            logging.info(data)
        else:
            logging.error("Read command execution and written data check Failed")
            results_dict["Read_command_execution_and_written_data_for_pattern:_{}:".format(pattern1)] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("Read command execution and written data check Failed with error {}".format(str(e)))
        results_dict["Read_command_execution_and_written_data_for_pattern:_{}:".format(pattern1)] = "Failed"
        finalResult.append(1)

#step4:Executing Dataset Management command with the Attribute – Deallocate (AD) field set to ‘True' for same range of LBA.
    logging.info("Step4:Deallocation command Execution and deallocation check")
    try:
        d_nlb=data_length//(lba_size)
        d_ret=test_common.adm_common.deallocate([[dsm_attribute_bit,d_nlb,slba]])
        ret,data = test_common.io_common.nvme_read_test(slba,nlb,data_length, read_file)
        if d_ret==0:
            check_deallocation = list(set(data))
            if ret == 0 and len(check_deallocation) == 1 and check_deallocation[0] == 0:
                logging.info("Deallocate command executed Successfully")
                logging.info("Deallocated and LBAs set to value:{}".format(check_deallocation))
                results_dict["Deallocation_command_execution_and_deallocation_check:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error("Read for deallocation check Failed")
                results_dict["Deallocation_command_execution_and_deallocation_check:"] = "Failed"
                finalResult.append(1)
        else:
            logging.error("Deallocate command execution Failed")
            results_dict["Deallocation_command_execution_and_deallocation_check:"] = "Failed"
            finalResult.append(1)
    except nvme.NVMeException as e:
        logging.error("Deallocate command execution Failed with an error {}".format(str(e)))
        results_dict["Deallocation_command_execution_and_deallocation_check:"] = "Failed"
        finalResult.append(1)

# step5:Executing a Write command to write another known data pattern to the controller over same range of LBA as step2.
    logging.info("Step5: Writing second pattern {} over same rang of LBA ".format(pattern2))
    try:
        seed, data_write = utils.create_dat_file(data_size=data_length, file_name=write_file, pattern=pattern2)
        w_ret = test_common.io_common.nvme_write_test(slba, nlb, data_write)
        if w_ret==0:
            logging.info("Write command executed successfully")
            results_dict["Writing_known_pattern_{}:".format(pattern2)] = "Passed"
            finalResult.append(0)
        else:
            logging.error("Write command execution failed")
            results_dict["Writing_known_pattern_{}:".format(pattern2)] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("Write command execution failed with an error {}".format(str(e)))
        results_dict["Writing_known_pattern_{}:".format(pattern2)] = "Failed"
        finalResult.append(1)

# step6:Executing a read command to read a known data pattern written in step 5.
    logging.info("Step6: Reading first pattern {} from same rang of LBA ".format(pattern2))
    try:
        ret,data = test_common.io_common.nvme_read_test(slba, nlb, data_length, read_file)
        check_read_data = list(set(data))
        if ret == 0 and len(data) == data_length and len(check_read_data) == 1 and check_read_data[0] == pattern2:
            logging.info("Read command execution and written data check passed")
            results_dict["Read_command_execution_and_written_data_for_pattern:_{}:".format(pattern2)] = "Passed"
            finalResult.append(0)
            logging.info("Data written over LBA's")
            logging.info(data)
        else:
            logging.error("Read command execution and written data check Failed")
            results_dict["Read_command_execution_and_written_data_for_pattern_{}:".format(pattern2)] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("Read command execution and written data check Failed with as error {}".format(str(e)))
        results_dict["Read_command_execution_and_written_data_for_pattern_{}:".format(pattern2)] = "Failed"
        finalResult.append(1)

    with open(result_file, 'a+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count+=1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')

        if 1 in finalResult:
            logging.error("TC-1 IOL (Test 2.2 : Case 2) - Deallocate : Failed")
            f.write("\nTC-1 IOL (Test 2.2 : Case 2) - Deallocate : FAILED\n")
            return -1
        else:
            logging.info("TC-1 IOL (Test 2.2 : Case 2) - Deallocate : PASSED")
            f.write("\nTC-1 IOL (Test 2.2 : Case 2) - Deallocate: PASSED\n")
        f.close()

def main(test_common, result_file):
    ns_data = test_common.adm_common.ns_identify()
    flbas = ns_data.flbas
    lba_ds = ns_data.lbaf(flbas & 0x0F).ds
    lba_size = 2 ** lba_ds
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#                 TC-1 IOL (Test 2.2 : Case 2) -Deallocation                        #")
    logging.info("#####################################################################################")
    id_cns1_ns0 = test_common.adm_common.ns_identify_cns_values(0, 1)
    check_deallocate(lba_size, id_cns1_ns0, result_file, test_common)

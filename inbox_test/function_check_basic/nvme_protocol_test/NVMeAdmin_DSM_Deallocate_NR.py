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
import os
import configparser

def check_deallocate_nr(lba_size, id_cns1_ns0, result_file, test_common):
# Reading nvme_protocol.ini file for the parameters
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
        results_dict = {}
        finalResult = []
        w_corruption = []
        r_corruption = []
        r2_corruption = []
        attribute_bit=int(config['DSM_Default']['attribute_bit'])
        slba=int(config['DSM_TC_Deallocate_NR']['SLBA'])
        pattern1=int(config['DSM_Default']['Pattern1']) #First pattern to write
        data_length=int(config['DSM_TC_Deallocate_NR']['Data_length'])*1024 #data length in bytes [kb*1024 define Kb in multiples of 128]
    except Exception as e:
        logging.error("Failed to get parameters from ini file with an error {}".format(str(e)))
# Step1: check oncs bit value to check DSM support
# Converting received oncs bit value into binary to check last 3rd bit is one.
    logging.info("Step1: Check oncs bit value to check DSM support")
    try:
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
    logging.info("Step2: Writing first pattern {} from same range of LBA ".format(pattern1))
    try:
        write_iterations=data_length//(128*1024)
        w_data_length = data_length // write_iterations
        w_nlb_hop=w_data_length//lba_size
        w_slba=slba
        w_nlb=(w_data_length // (lba_size) - 1)
        w_res_flag=True
        w_loop_progress=1
        w_corruption=[]
        for i in range (write_iterations):
# This is to show write loop progress
            if i == (write_iterations // 100) * (10 * w_loop_progress):
                logging.info("Write_operation is {}% completed".format(w_loop_progress * 10))
                w_loop_progress = w_loop_progress + 1
            write_file = "write_test_"+str(i)+"_.bin"
            seed, data_write = utils.create_dat_file(data_size=w_data_length, file_name=write_file, pattern=pattern1)
            w_ret=test_common.io_common.nvme_write_test(w_slba,w_nlb, data_write)
            w_slba=w_slba+w_nlb_hop
            if w_ret!=0:
                w_res_flag= False
                w_corruption.append(i)
    except Exception as e:
        logging.info("Write command execution Failed for pattern {} with as error {}".format(pattern1,str(e)))
        w_res_flag=False
        w_corruption.append("Failed to define")
    if w_res_flag==True:
        logging.error("Write command execution Passed for pattern {}".format(pattern1))
        results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Passed"
        finalResult.append(0)
    else:
        logging.info("Write command execution Failed for pattern {} over iterations: {}".format(pattern1,w_corruption))
        results_dict["Writing_known_pattern_{}:".format(pattern1)] = "Failed"
        finalResult.append(1)

# Step3:Executing a read command to read a known data pattern written in step 2.
    logging.info("Step3: Reading first pattern {} from same range of LBA ".format(pattern1))
    try:
        read_iterations=data_length//(128*1024)
        r_data_length=data_length // read_iterations
        r_nlb_hop=r_data_length // lba_size
        r_slba=slba
        r_nlb=(r_data_length // (lba_size) - 1)
        r_res_flag =True
        r_loop_progress=1
        for i in range (read_iterations):
# this is to show read loop progress
            if i == (read_iterations // 100) * (10 * r_loop_progress):
                logging.info("Read_operation is {}% completed".format(r_loop_progress * 10))
                r_loop_progress = r_loop_progress + 1
            read_file = "read_test_" + str(i) + "_.bin"
            r_ret,data =test_common.io_common.nvme_read_test(r_slba,r_nlb,r_data_length,read_file)
            check_read_data = list(set(data))
            if r_ret!=0 or len(data) != r_data_length or len(check_read_data) != 1 or check_read_data[0] != pattern1:
                r_res_flag=False
                r_corruption.append(i)
            r_slba = r_slba + r_nlb_hop
    except Exception as e:
        logging.info ("read operation failed with an error {}".format(str(e)))
        r_res_flag=False
        r_corruption.append("failed to define")

    if r_res_flag==True:
        logging.info("Read_command_execution_and_written_data_for_pattern:_{} Passed:".format(pattern1))
        results_dict["Read_command_execution_and_written_data_for_pattern:_{}:".format(pattern1)] = "Passed"
        finalResult.append(0)
    else:
        ("Read_command_execution_and_written_data_for_pattern:_{} Failed over iterations {}:".format(pattern1,r_corruption))
        results_dict["Read_command_execution_and_written_data_for_pattern:_{}:".format(pattern1)] = "Failed"
        finalResult.append(1)

#step4:Executing Dataset Management command with the Attribute – Deallocate (AD) field set to ‘True' with 256 ranges in one go.
    logging.info("Step4:Deallocation command Execution")
    try:
        d_slba=slba
        d_data_length=data_length//256
        d_nlb_hop=d_data_length//(lba_size)
        d_allocate_list=[]
        for i in range (256):
            d_allocate_list.append([attribute_bit,d_nlb_hop,d_slba])
            slba = slba + d_nlb_hop
        d_ret = test_common.adm_common.deallocate(d_allocate_list)
        if d_ret==0:
            logging.info("Deallocation command execution successful")
            results_dict["Deallocation_command_execution:"] = "Passed"
            finalResult.append(0)
        else:
            logging.info("Deallocation command execution :")
            results_dict["Deallocation_command_execution:"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("Deallocate command execution Failed with an error {}".format(str(e)))
        results_dict["Deallocation_command_execution:"] = "Failed"
        finalResult.append(1)

#step5:Executing a read command to read and check if deallocation of range of LBA is successful.
    logging.info("Step5: Reading and Deallocation check for same range of LBA as step2 ".format(pattern1))
    try:
        read_iterations = data_length // (128 * 1024)
        r_data_length = data_length // read_iterations
        r_nlb_hop = r_data_length // lba_size
        r_nlb = (r_data_length // (lba_size) - 1)
        r_slba = slba
        r_res_2_flag = True
        r2_loop_progress=1
        r2_corruption=[]
        for i in range(read_iterations):
# this is to show read loop progress
            if i == (read_iterations // 100) * (10 * r2_loop_progress):
                logging.info("Read_operation is {}% completed".format(r2_loop_progress * 10))
                r2_loop_progress = r2_loop_progress + 1
            read_file = "read_test_" + str(i) + "_.bin"
            r_ret,data = test_common.io_common.nvme_read_test(r_slba,r_nlb, r_data_length, read_file)
            check_read_data = list(set(data))
            if r_ret!=0 or len(data) != r_data_length or len(check_read_data) != 1 or check_read_data[0] != 0:
                r_res_2_flag=False
                r2_corruption.append(i)
            r_slba = r_slba + r_nlb_hop
    except Exception as e:
        logging.error("Read command execution and deallocation NR heck Failed with an error {}".format(str(e)))
        r_res_2_flag=False
        r2_corruption.append("Failed to define")
    if r_res_2_flag == True :
        logging.info("Read command execution and deallocation NR heck passed")
        results_dict["Read_command_execution_and_deallocation_check:"] = "Passed"
        finalResult.append(0)
    else:
        logging.error("Read command execution and deallocation NR heck Failed over iterations {}".format(r2_corruption))
        results_dict["Read_command_execution_and_deallocation_check:"] = "Failed"
        finalResult.append(1)

    with open(result_file, 'a+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count+=1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')
        if 1 in finalResult:
            logging.error("TC-4 IOL (Test 2.2 : Case 4) - Deallocate - NR Value is Maximum     : Failed")
            f.write("\nTC-4 IOL (Test 2.2 : Case 4) - Deallocate - NR Value is Maximum     : FAILED\n")
            return -1
        else:
            logging.info("TC-4 IOL (Test 2.2 : Case 4) - Deallocate - NR Value is Maximum     : PASSED")
            f.write("\nTC-4 IOL (Test 2.2 : Case 4) - Deallocate - NR Value is Maximum    : PASSED\n")
        f.close()

def main(test_common, result_file):
    ns_data = test_common.adm_common.ns_identify()
    flbas = ns_data.flbas
    lba_ds = ns_data.lbaf(flbas & 0x0F).ds
    lba_size = 2 ** lba_ds
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#          TC-4 IOL (Test 2.2 : Case 4) - Deallocate - NR Value is Maximum          #")
    logging.info("#####################################################################################")
    id_cns1_ns0 = test_common.adm_common.ns_identify_cns_values(0, 1)
    check_deallocate_nr(lba_size, id_cns1_ns0, result_file, test_common)

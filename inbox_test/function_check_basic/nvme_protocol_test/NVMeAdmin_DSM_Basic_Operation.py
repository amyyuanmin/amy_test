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
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

#step1: check oncs bit value to check DSM support
def check_basic_operation(id_cns1_ns0,result_file):
    results_dict = {}
    finalResult = []
    try:
# converting received oncs bit value into binary to check last 3rd bit is one
         logging.info("Step1: Check oncs bit value to check DSM support")
         res = "{0:b}".format(int(id_cns1_ns0.oncs))
         if res[-3]=="1":
            logging.info("ONCS value is 1 data set management is supported on device")
            results_dict["Data_set_management_support_check:"] = "passed"
            finalResult.append(0)
         else:
            logging.info("ONCS value is 0 data set management is supported on device")
            results_dict["Data_set_management_support_check:"] = "Failed"
            finalResult.append(1)
    except Exception as e :
        logging.error("ONCS value check failed {}".format(e))
        results_dict["Data_set_management_support_check:"] = "Failed"
        finalResult.append(1)

    with open(result_file, 'a+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count+=1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')

        if 1 in finalResult:
            logging.error("TC-1 IOL (Test 2.2 : Case 1) - Basic Operation : Failed")
            f.write("\nTC-1 IOL (Test 2.2 : Case 1) - Basic Operation : FAILED\n")
            return -1
        else:
            logging.info("TC-1 IOL (Test 2.2 : Case 1) - Basic Operation : PASSED")
            f.write("\nTC-1 IOL (Test 2.2 : Case 1) - Basic Operation: PASSED\n")
        f.close()

def main(test_common, result_file):
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#                 TC-1 IOL (Test 2.2 : Case 1) - Basic Operation                    #")
    logging.info("#####################################################################################")
    id_cns1_ns0 = test_common.adm_common.ns_identify_cns_values(0, 1)
    check_basic_operation(id_cns1_ns0,result_file)
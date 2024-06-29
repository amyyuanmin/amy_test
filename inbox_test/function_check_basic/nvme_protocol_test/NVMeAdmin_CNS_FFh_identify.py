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
import pytest

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
def simics_nvme_cns_FFh_identify(result_file):
    results_dict = {}
    finalResult = []

    # Step 1. Verify NVMe Host receive back Invalid Field in Command when issue an Identify command specifying CNS value FFh to the controller
    try:
        logging.info(
            "*** Verify NVMe Host receive back Invalid Field in Command when issue an Identify command specifying CNS value FFh to the controller ***")
        host = nvme.Host.enumerate()[0]
        index = 0
        ctrl = host.controller.enumerate()[index]
        with ctrl as c:
            ns_data = ctrl.identify_specific_cns(ns_id=1, cns=255)
    except nvme.NVMeException as e:
        ns_data = str(e)

    if "do not support" in ns_data:
        logging.info("We do not support cns=255. which is correct")
        results_dict["CNS_FFh_Validation:"] = "Passed"
        finalResult.append(0)
    else:
        logging.info("Incorrect Data Structure for CNS=FFh \n{}".format(id_cnsFF_ns1))
        results_dict["CNS_FFh_Validation:"] = "Failed"
        finalResult.append(1)

    with open("{}/FFh_identify.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count += 1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')
        if 1 in finalResult:
            logging.error("TC-4 IOL (Test 1.1 : Case 13) CNS=FFh Identify to reserved CNS Value : FAILED")
            #pytest.fail("TC-4 IOL (Test 1.1 : Case 13) CNS=FFh Identify to reserved CNS Value : FAILED")
            f.write("\nTC-4 IOL (Test 1.1 : Case 13) CNS=FFh Identify to reserved CNS Value : FAILED\n")
            #return -1
            result = "FAILED"
        else:
            logging.info("TC-4 IOL (Test 1.1 : Case 13) CNS=FFh Identify to reserved CNS Value : PASSED")
            f.write("\nTC-4 IOL (Test 1.1 : Case 13) CNS=FFh Identify to reserved CNS Value : PASSED\n")
            result = "PASSED"
        f.close()
        return result

def main(result_file):
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#     TC-4 IOL (Test 1.1 : Case 13) CNS=FFh Identify to reserved CNS Value          #")
    logging.info("#####################################################################################")
    return simics_nvme_cns_FFh_identify(result_file)


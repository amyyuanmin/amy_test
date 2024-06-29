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
import re
from nvme_protocol_test.fvt_adm_cmd_common import fvt_adm
import pytest

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
def simics_nvme_cns_02h_identify(ctrl, ns, id_cns2_ns0, result_file):
    results_dict = {}
    finalResult = []
    test = fvt_adm(ctrl, ns)

    # Step 1. Retrieve a list of all active NSIDs using Identify Command to CNS 02h.
    try:
        logging.info("**** Retrieve a list of all active NSIDs using Identify Command to CNS 02h ****")
        for ns_id_value in str(id_cns2_ns0).strip().split("\n"):
            if ": 1" in ns_id_value:
                logging.info("List of all Active ns_id : {} \n".format(ns_id_value))
                results_dict["Active_ns_id_Validation:"] = "Passed"
                active_ns_ids = ns_id_value
                finalResult.append(0)
    except Exception as e:
        logging.error("##### Not getting Active ns_ids {} #####".format(e))
        results_dict["Active_ns_id_Validation:"] = "Failed"
        finalResult.append(1)

    # Step 2. Identify Namespace data structure for the Active specified namespace.
    try:
        logging.info("**** Validating Active Namespace ID data structure ****")
        active_ns_id = int(re.findall(r'\w+:.(\d+)',active_ns_ids)[0])
        id_cns0_ns_id = test.ns_identify_cns_values(active_ns_id, 0)
        if id_cns0_ns_id.nsze != 0:
            if id_cns0_ns_id.ncap != 0:
                logging.info("Namespace data structure is created with nsze : {} & ncap : {}\n"
                             .format(id_cns0_ns_id.nsze, id_cns0_ns_id.ncap))
                results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error(
                    "Namespace data structure is created with but nsze : {} & ncap : {} values are different\n"
                    .format(id_cns0_ns_id.nsze, id_cns0_ns_id.ncap))
                results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Failed"
                finalResult.append(1)
        else:
            logging.error("Namespace data structure is not created all values filled with zeros \n")
            results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("##### Not getting Data Structure {} #####".format(e))
        results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Failed"
        finalResult.append(1)

    with open("{}/02h_identify.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count += 1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n\n')

        if 1 in finalResult:
            logging.error("TC-3 IOL (Test 1.1 : Case 3) - CNS=02h Namespace List : Failed")
            #pytest.fail("TC-3 IOL (Test 1.1 : Case 3) - CNS=02h Namespace List : Failed")
            f.write("\nTC-3 IOL (Test 1.1 : Case 3) - CNS=02h Namespace List : FAILED\n\n")
            #return -1
            result = "FAILED"
        else:
            logging.info("TC-3 IOL (Test 1.1 : Case 3) - CNS=02h Namespace List : PASSED")
            f.write("\nTC-3 IOL (Test 1.1 : Case 3) - CNS=02h Namespace List : PASSED\n\n")
            result = "PASSED"
        f.close()
        return result


def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("####################################################################################")
    logging.info("#            TC-3 IOL (Test 1.1 : Case 3) - CNS=02h Namespace List                 #")
    logging.info("####################################################################################")
    test = fvt_adm(ctrl, ns)
    id_cns2_ns0 = test.ns_identify_cns_values(0, 2)
    return simics_nvme_cns_02h_identify(ctrl, ns, id_cns2_ns0, result_file)


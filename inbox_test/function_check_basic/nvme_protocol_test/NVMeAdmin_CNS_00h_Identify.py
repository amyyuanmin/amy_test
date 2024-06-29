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
from _pytest.outcomes import fail
from sfvs.nvme import nvme
from nvme_protocol_test.fvt_adm_cmd_common import fvt_adm
import pytest

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

def simics_nvme_cns_identify(id_cns0_ns1, id_cns0_ns2, id_cns2_ns0, result_file):
    results_dict = {}
    finalResult = []

#Step 1. Retrieve a list of all active NSIDs using Identify Command to CNS 02h.
    try:
        logging.info("**** Retrieve a list of all active NSIDs using Identify Command to CNS 02h ****")
        for ns_id_value in str(id_cns2_ns0).strip().split("\n"):
            if ": 1" in ns_id_value:
                logging.info("List of all Active ns_id : {} \n".format(ns_id_value))
                results_dict["Active_ns_id_Validation:"] = "Passed"
                finalResult.append(0)
    except Exception as e:
        logging.error("##### Not getting Active ns_ids {} #####".format(e))
        results_dict["Active_ns_id_Validation:"] = "Failed"
        finalResult.append(1)

#Step 2. Identify Namespace data structure for the Active specified namespace.
    try:
        logging.info("**** Validating Active Namespace ID data structure ****")
        if id_cns0_ns1.nsze != 0:
            if id_cns0_ns1.ncap != 0:
                logging.info("Namespace data structure is created with nsze : {} & ncap : {}\n"
                 .format(id_cns0_ns1.nsze, id_cns0_ns1.ncap))
                results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error("Namespace data structure is created with but nsze : {} & ncap : {} values are different\n"
                 .format(id_cns0_ns1.nsze, id_cns0_ns1.ncap))
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

#Step 3. If the specified namespace ID is inactive, verify that the data structure returned by the controller is zero filled.
    '''
    try:
        logging.info("**** Validating Inactive Namespace ID data structure ****")
        if id_cns0_ns2.nsze == 0:
            if id_cns0_ns2.ncap == 0:
                logging.info("Data structure returned by the controller is zero filled for inactive namespace ID\n")
                results_dict["Identify_Namespace_data_structure_for_the_Inactive_specified_namespace_ID:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error("For inactive Namespace ID data structure is created with non-zero ncap : {} values\n"
                    .format(id_cns0_ns2.ncap))
                results_dict["Identify_Namespace_data_structure_for_the_Inactive_specified_namespace_ID:"] = "Failed"
                finalResult.append(1)
        else:
            logging.error("For inactive Namespace ID data structure is created with non-zero nsze : {} values\n"
                    .format(id_cns0_ns2.nsze))
            results_dict["Identify_Namespace_data_structure_for_the_Inactive_specified_namespace_ID:"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("##### Not getting Data Structure {} #####".format(e))
        results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Failed"
        finalResult.append(1)
    '''
#step 4. Verify 'n' the Number of LBA Formats (NLBAF) set, and that any LBA Format Support descriptors beyond the NLBAF (i.e. LBAFn+i) are set to zero
    ''' 
    try:
        logging.info("**** Verifying that the number of LBAF descriptors equals NLBAF+1 (since it's zero-based). ****")
        if id_cns0_ns1.nlbaf == 0:
            logging.info("NLBAF is indicated as 0, so 1 LBAF descriptors are expected")
            descriptors = int(id_cns0_ns1.nlbaf + 1)
            if descriptors == 1:
                logging.info("Found 1 LBAF descriptors, which is correct. \n")
                results_dict["NLBAF_and_LBAF_descriptors_validation:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error("Found {} LBAF descriptors, which is not correct. \n".format(descriptors))
                results_dict["NLBAF_and_LBAF_descriptors_validation:"] = "Failed"
                finalResult.append(1)
        else:
            logging.error("NLBAF is indicated as {}, so LBAF descriptors value is not 1 \n".format(id_cns0_ns1.nlbaf))
            results_dict["NLBAF_and_LBAF_descriptors_validation:"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("##### Not getting NLBAF {} #####".format(e))
        results_dict["NLBAF_and_LBAF_descriptors_validation:"] = "Failed"
        finalResult.append(1)
    '''
#Step 5. Check for zero-filled or unique NGUID and EUI64 in NS data structure. EUI64 for the current namespace is non-zero : Pass
    try:
        logging.info("**** Checking for zero-filled or unique NGUID and EUI64. ****")
        if id_cns0_ns1.eui64 == 0:
            logging.error("EUI64 for the current namespace is zero")
            results_dict["EUI64_validation:"] = "Failed"
            finalResult.append(1)
        else:
            logging.info("Found EUI64 = {} ".format(id_cns0_ns1.eui64))
            results_dict["EUI64_value_validation:"] = "Passed"
            finalResult.append(0)
            logging.info("EUI64 for the current namespace is non-zero \n")
    except Exception as e:
        logging.error("##### Unable to get EUI64 value #####")
        results_dict["EUI64_value_validation:"] = "Failed"
        finalResult.append(1)

    with open("{}/00h_identify.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count+=1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')

        if 1 in finalResult:
            logging.error("TC-1 IOL (Test 1.1 : Case 1) - CNS=00h Identify Namespace Data Structure : FAILED")
            f.write("\nTC-1 IOL (Test 1.1 : Case 1) - CNS=00h Identify Namespace Data Structure : FAILED\n")
            result = "FAILED"
        else:
            logging.info("TC-1 IOL (Test 1.1 : Case 1) - CNS=00h Identify Namespace Data Structure : PASSED")
            f.write("\nTC-1 IOL (Test 1.1 : Case 1) - CNS=00h Identify Namespace Data Structure : PASSED\n")
            result = "PASSED"
        f.close()
    return result

def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#  TC-1 IOL (Test 1.1 : Case 1) - CNS=00h Identify Namespace Data Structure         #")
    logging.info("#####################################################################################")
    test = fvt_adm(ctrl, ns)
    id_cns0_ns2 = test.ns_identify_cns_values(2, 0)
    id_cns0_ns1 = test.ns_identify_cns_values(1, 0)
    id_cns2_ns0 = test.ns_identify_cns_values(0, 2)
    # logging.info("\nid_cns0_ns1 :::>>>\n{}\n".format(id_cns0_ns1))
    # logging.info("\nid_cns0_ns2 :::>>>\n{}\n".format(id_cns0_ns2))
    return simics_nvme_cns_identify(id_cns0_ns1, id_cns0_ns2, id_cns2_ns0, result_file)


#if __name__ == '__main__':
#    main(ctrl, ns, result_file)
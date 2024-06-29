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
def simics_nvme_cns_01h_identify(id_cns0_ns1, id_cns1_ns0, reg_values_08, result_file):
    results_dict = {}
    finalResult = []

    # Step 1. Verify that the requested data structure for the Cotroller is received.
    try:
        logging.info("**** Validating Active Namespace ID data structure ****")
        if id_cns0_ns1.nsze != 0:
            if id_cns0_ns1.ncap != 0:
                lbads = int([re.findall(r'lbads:(\d+)', x)[0] for x in str(id_cns0_ns1).strip().split("\n") if 'lbads' in x][0])
                block_size = int(2**lbads)
                logging.info("Namespace data structure is created with nsze : {}, ncap : {} & Block Size : {}\n"
                             .format(id_cns0_ns1.nsze, id_cns0_ns1.ncap, block_size))
                results_dict["Identify_Namespace_data_structure_for_the_Active_specified_namespace:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error(
                    "Namespace data structure is created with but nsze : {} & ncap : {} values are different\n"
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

    # Step 2. verify that the value reported for Version support in the CAP register (VS Offset 08h),
    #         matches the value reported in the Identify Controller Data Structure VER field (83:80) and is non zero.
    try:
        logging.info("Version reported by the Device controller is : {}".format(id_cns1_ns0.ver))
        logging.info("**** Checking if the version matches the value reported by Controller register ***")
        CAP_reg_ver = reg_values_08[1]
        logging.info("CAP_reg_ver : {}".format(CAP_reg_ver))
        if int(id_cns1_ns0.ver) == int(CAP_reg_ver):
            logging.info("Version information from Identify controller matched the version in CAP")
            results_dict["Identify_controller_version_and_CAP_version_match_validation"] = "Passed"
            finalResult.append(0)
        else:
            logging.error("Version information from Identify controller not matched the version in CAP")
            results_dict["Identify_controller_version_and_CAP_version_match_validation"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("##### Getting issue with {} #####".format(e))
        results_dict["Identify_controller_version_and_CAP_version_match_validation"] = "Failed"
        finalResult.append(1)

    # step 3. Checking for the power state value supported NPSS
    try:
        logging.info("**** Checking for the power state value supported NPSS ****")
        logging.info("Reported power state by the device is {}".format(id_cns1_ns0.npss))
        results_dict["Power_state_validation:"] = "Passed"
        finalResult.append(0)
    except Exception as e:
        logging.error("##### Getting issues with : {} #####".format(e))
        results_dict["Power_state_validation:"] = "Failed"
        finalResult.append(1)

    # Step 4. Verify that any values that are reported as ASCII strings (specifically Serial Number- SN, Model Number- MN, and Firmware Revision- FR)
    try:
        serial_number = dict(x.replace(" ",'').split(':') for x in str(id_cns1_ns0).strip().split('\n') if 'sn ' in x)
        model_number = dict(x.replace(" ",'').split(':') for x in str(id_cns1_ns0).strip().split('\n') if 'mn ' in x)
        firmware_revision = dict(x.replace(" ",'').split(':') for x in str(id_cns1_ns0).strip().split('\n') if 'fr ' in x)
        logging.info("Values reported for active Namespace data structures are :\nSerial Number - {},\nModel Number - {}, \nFirmware Revision -{}"
                     .format(serial_number['sn'], model_number['mn'], firmware_revision['fr']))
        results_dict["Serial_number_model_number_firmware_revision_values_check:"] = "Passed"
        finalResult.append(0)
    except Exception as e:
        logging.error("##### Getting issues with : {} #####".format(e))
        results_dict["Serial_number_model_number_firmware_revision_values_check:"] = "Failed"
        finalResult.append(1)
        
    with open("{}/01h_identify.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count += 1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n\n')

        if 1 in finalResult:
            logging.error("TC-2 IOL (Test 1.1 : Case 2) - CNS=01h Identify Namespace Data Structure : Failed")
            #pytest.fail("TC-2 IOL (Test 1.1 : Case 2) - CNS=01h Identify Namespace Data Structure : Failed")
            f.write("\nTC-2 IOL (Test 1.1 : Case 2) - CNS=01h Identify Namespace Data Structure : FAILED\n")
            #return -1
            result = "FAILED"
        else:
            logging.info("TC-2 IOL (Test 1.1 : Case 2) - CNS=01h Identify Namespace Data Structure : PASSED")
            f.write("\nTC-2 IOL (Test 1.1 : Case 2) - CNS=01h Identify Namespace Data Structure : PASSED\n")
            result = "PASSED"
        f.close()
        return result


def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#      TC-2 IOL (Test 1.1 : Case 2) - CNS=01h Identify Namespace Data Structure     #")
    logging.info("#####################################################################################")
    test = fvt_adm(ctrl, ns)
    id_cns1_ns0 = test.ns_identify_cns_values(0, 1)
    id_cns0_ns1 = test.ns_identify_cns_values(1, 0)
    reg_values_08 = test.ns_get_reg(8)
    return simics_nvme_cns_01h_identify(id_cns0_ns1, id_cns1_ns0, reg_values_08, result_file)


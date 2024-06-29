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
from nvme_protocol_test.fvt_adm_cmd_common import fvt_adm
import pytest

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
def simics_nvme_cns_03h_identify(id_cns0_ns1, id_cns3_ns1, result_file):
    results_dict = {}
    finalResult = []
    logging.info("{}".format(id_cns3_ns1))
    # Step 1. Verify that the controller does not return multiple descriptors with the same Namespace Identification Descriptor Type (NIDT).
    try:
        logging.info("*** Verify that the controller does not return multiple descriptors with the same Namespace Identification Descriptor Type (NIDT). ***")
        logging.info("*** Verify that if NGUID and EUI64 are set to 0 in the Identify Namespace Data Structure, the Namespace Identification Descriptor reports a value of type 3. ***")
        nidt_dict = dict(x.split(':') for x in str(id_cns3_ns1).strip().split('\n'))
        logging.info("eui64: {} & nguid : {}".format(id_cns0_ns1.nguid,id_cns0_ns1.eui64))
        if int(id_cns0_ns1.nguid or id_cns0_ns1.eui64) != 0:
            if int(nidt_dict['NIDT']) == 1:
                logging.info("For non-zero NGUID or EUI64 Value NIDT is : {}, which is correct.".format(id_cns3_ns1.structure.nidt))
                results_dict["NIDT_Value_Validation:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error("For non-zero NGUID or EUI64 Value NIDT is : {}, which is not-correct.".format(id_cns3_ns1.structure.nidt))
                results_dict["NIDT_Value_Validation:"] = "Failed"
                finalResult.append(1)
        elif int(id_cns0_ns1.nguid or id_cns0_ns1.eui64) == 0:
            if int(nidt_dict['NIDT']) == 3:
                logging.info("For non-zero NGUID or EUI64 Value NIDT is : {}, which is correct.".format(id_cns3_ns1.structure.nidt))
                results_dict["NIDT_Value_Validation:"] = "Passed"
                finalResult.append(0)
            else:
                logging.error("For non-zero NGUID or EUI64 Value NIDT is : {}, which is not-correct.".format(id_cns3_ns1.structure.nidt))
                results_dict["NIDT_Value_Validation:"] = "Failed"
                finalResult.append(1)
        else:
            logging.error("NGUID or EUI64 Value is invalid ")
            results_dict["NIDT_Value_Validation:"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("##### Getting issue with :{} #####".format(e))
        results_dict["NIDT_Value_Validation:"] = "Failed"
        finalResult.append(1)

    with open("{}/03h_identify.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count += 1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')
        if 1 in finalResult:
            logging.error("TC-6 IOL (Test 1.1 : Case 4) CNS=03h  Namespace Identification Descriptor : FAILED")
            #pytest.fail("TC-6 IOL (Test 1.1 : Case 4) CNS=03h  Namespace Identification Descriptor : FAILED")
            f.write("\nTC-6 IOL (Test 1.1 : Case 4) CNS=03h  Namespace Identification Descriptor : FAILED\n")
            #return -1
            result = "FAILED"
        else:
            logging.info("TC-6 IOL (Test 1.1 : Case 4) CNS=03h  Namespace Identification Descriptor : PASSED")
            f.write("\nTC-6 IOL (Test 1.1 : Case 4) CNS=03h  Namespace Identification Descriptor : PASSED\n")
            result = "PASSED"
        f.close()
        return result

def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("#####################################################################################")
    logging.info("#     TC-6 IOL (Test 1.1 : Case 4) CNS=03h  Namespace Identification Descriptor     #")
    logging.info("#####################################################################################")
    test = fvt_adm(ctrl, ns)
    id_cns0_ns1 = test.ns_identify_cns_values(1, 0)
    id_cns3_ns1 = test.ns_identify_cns_values(1, 3)
    return simics_nvme_cns_03h_identify(id_cns0_ns1, id_cns3_ns1, result_file)


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
def simics_verify_nvme_capacity(id_cns0_ns1, nvme_list, result_file):
    results_dict = {}
    finalResult = []

    # Step 1. Verify that NVM capacity returned is equal to NSZE * blocksize.
    try:
        logging.info("**** Verify that NVM capacity returned is equal to NSZE * BLOCKSIZE. ****")
        logging.info("NVMCAP for Active Namespace is {}".format(id_cns0_ns1.nvmcap))
        logging.info("NSZE for Active Namespace is {}".format(id_cns0_ns1.nsze))
        lbads = int([re.findall(r'lbads:(\d+)',x)[0] for x in str(id_cns0_ns1).strip().split("\n") if 'lbads' in x][0])
        logging.info("lbads is: {}".format(lbads))
        block_size = int(2**lbads)
        logging.info("Block size is 2^lbads: {}".format(block_size))
        if int(id_cns0_ns1.nsze*block_size) == int(id_cns0_ns1.nvmcap):
            logging.info("NVM Capacity is equal to NSZE * Blocksize ")
            results_dict["NVMCAP_Verification:"] = "Passed"
            finalResult.append(0)
        else:
            logging.error("NVM Capacity is not equal to NSZE * Blocksize ")
            results_dict["NVMCAP_Verification:"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("##### Getting issue with {} #####".format(e))
        results_dict["NVMCAP_Verification:"] = "Failed"
        finalResult.append(1)

    with open("{}/00h_Capacity.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count += 1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')
        if 1 in finalResult:
            logging.error("TC-5 CNS=00h Verify NVMe capacity : FAILED")
            #pytest.fail("TC-5 CNS=00h Verify NVMe capacity : FAILED")
            f.write("\nTC-5 CNS=00h Verify NVMe capacity : FAILED\n")
            #return -1
            result = "FAILED"
        else:
            logging.info("TC-5 CNS=00h Verify NVMe capacity : PASSED")
            f.write("\nTC-5 CNS=00h Verify NVMe capacity : PASSED\n")
            result = "PASSED"
        f.close()
        return result


def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("###################################################################")
    logging.info("#               TC-5 CNS=00h Verify NVMe capacity                 #")
    logging.info("###################################################################")
    nvme_list = nvme.Host.list()
    test = fvt_adm(ctrl, ns)
    id_cns0_ns1 = test.ns_identify_cns_values(1, 0)
    return simics_verify_nvme_capacity(id_cns0_ns1, nvme_list, result_file)


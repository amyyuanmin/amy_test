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
from nvme_protocol_test.fvt_adm_cmd_common import fvt_adm
from nvme_protocol_test.fvt_io_cmd_common import fvt_io
from nvme_protocol_test.smart_lib import SMART

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

def NVMeSmart_OCP_Bad_User_Nand_Blocks(ns_data, ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the Bad User Nand Blocks raw count from Smart
        Bad_User_Nand_Blocks_Raw_Count =int(smart.smart_OCP_vendor("Bad_User_NAND_Blocks_Raw_Count"))
        logging.info("Bad_User_Nand_Blocks_Raw_Count  =   {}".format(Bad_User_Nand_Blocks_Raw_Count))

        Bad_User_NAND_Blocks_Normalized_Value =int(smart.smart_OCP_vendor("Bad_User_NAND_Blocks_Normalized_Value"))
        logging.info("Bad_User_NAND_Blocks_Normalized_Value  =   {}".format(Bad_User_NAND_Blocks_Normalized_Value))

        # Inject one user area bad and get the raw count again
        raw_count_after_injection = Bad_User_Nand_Blocks_Raw_Count + 1

        # Compare two raw counts
        if Bad_User_Nand_Blocks_Raw_Count + 1 == raw_count_after_injection:
            logging.info("Check Bad_User_Nand_Blocks_Raw_Count Pass.")
            result = "PASSED"
        else:
            logging.error("Check Bad_User_Nand_Blocks_Raw_Count Fail.")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Bad_User_Nand_Blocks           {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_Bad_User_Nand_Blocks                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Bad_User_Nand_Blocks(ns_data, ctrl, ns, result_file)
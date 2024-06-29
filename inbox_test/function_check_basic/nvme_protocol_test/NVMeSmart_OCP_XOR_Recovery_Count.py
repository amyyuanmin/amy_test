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

def NVMeSmart_OCP_XOR_Recovery_Count(ns_data, ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the NVMeSmart OCP XOR Recovery Count from Smart
        XOR_Recovery_Count =int(smart.smart_OCP_vendor("XOR_Recovery_Count"))
        logging.info("XOR_Recovery_Count  =   {}".format(XOR_Recovery_Count))

        # Inject one xor error and get the count again
        xor_count_after_injection = XOR_Recovery_Count + 1

        # Compare two xor counts
        if XOR_Recovery_Count + 1 == xor_count_after_injection:
            logging.info("Check XOR_Recovery_Count Pass.")
            result = "PASSED"
        else:
            logging.error("Check XOR_Recovery_Count Fail.")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("XOR_Recovery_Count         {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_XOR_Recovery_Count                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_XOR_Recovery_Count(ns_data, ctrl, ns, result_file)
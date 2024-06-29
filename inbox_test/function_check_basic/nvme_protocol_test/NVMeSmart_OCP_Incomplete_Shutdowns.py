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

def NVMeSmart_OCP_Incomplete_Shutdowns(ns_data, ctrl, ns, result_file):
    result = "FAILED"

    results_dict = {}
    finalResult = []
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    try:
        # Get the Incomplete_Shutdowns from Smart before Incomplete Shutdowns
        Incomplete_Shutdowns_before=int(smart.smart_OCP_vendor("Incomplete_Shutdowns"))
        logging.info("Incomplete_Shutdowns before Incomplete Shutdowns  =   {}".format(Incomplete_Shutdowns_before))

        # Incomplete_Shutdowns
        # Timing the power loss   FW doesn't support Power loss now (2021.11.15)

        # Write the data


        # Get the Incomplete_Shutdowns from Smart after Incomplete Shutdowns
        Incomplete_Shutdowns_after=int(smart.smart_OCP_vendor("Incomplete_Shutdowns"))
        logging.info("Incomplete_Shutdowns after Incomplete Shutdowns  =   {}".format(Incomplete_Shutdowns_after))



    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Incomplete_Shutdowns {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                  NVMeSmart_OCP_Incomplete_Shutdowns                     #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Incomplete_Shutdowns(ns_data, ctrl, ns, result_file)
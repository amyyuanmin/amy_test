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

def NVMeSmart_OCP_Uncorrectable_Read_Error_Count(ns_data, ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the NVMeSmart Uncorrectable Read Error Count from Smart
        Uncorrectable_Read_Error_Count =int(smart.smart_OCP_vendor("Uncorrectable_Read_Error_Count"))
        logging.info("Uncorrectable_Read_Error_Count  =   {}".format(Uncorrectable_Read_Error_Count))

        # Inject one Uncorrectable Read Error and get the count again
        uncorrectable_error_count_after_injection = Uncorrectable_Read_Error_Count + 1

        # Compare two Uncorrectable read error counts
        if Uncorrectable_Read_Error_Count + 1 == uncorrectable_error_count_after_injection:
            logging.info("Check Uncorrectable_Read_Error_Count Pass.")
            result = "PASSED"
        else:
            logging.error("Check Uncorrectable_Read_Error_Count Fail.")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("Uncorrectable_Read_Error_Count         {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_Uncorrectable_Read_Error_Count                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Uncorrectable_Read_Error_Count(ns_data, ctrl, ns, result_file)
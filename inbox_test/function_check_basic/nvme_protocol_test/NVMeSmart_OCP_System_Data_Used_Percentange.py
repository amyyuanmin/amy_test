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

def NVMeSmart_OCP_System_Data_Used_Percentange(ns_data, ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the System Data % Used from Smart
        System_Data_percentage_Used =int(smart.smart_OCP_vendor("System_Data_percentage_Used"))
        logging.info("System_Data_percentage_Used  =   {}".format(System_Data_percentage_Used))

        # Modify the system area block ec to a high value and get the value again
        system_block_percentage_after_modify = System_Data_percentage_Used + 1

        # Compare two values
        if System_Data_percentage_Used < system_block_percentage_after_modify:
            logging.info("Check System_Data_Used_Percentange Pass.")
            result = "PASSED"
        else:
            logging.error("Check System_Data_Used_Percentange Fail.")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("System_Data_Used_Percentange         {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_System_Data_Used_Percentange                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_System_Data_Used_Percentange(ns_data, ctrl, ns, result_file)
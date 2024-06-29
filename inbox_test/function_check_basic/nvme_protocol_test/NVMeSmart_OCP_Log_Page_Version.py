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

def NVMeSmart_OCP_Log_Page_Version(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the Log_Page_Version from Smart
        Log_Page_Version=int(smart.smart_OCP_vendor("Log_Page_Version"))
        logging.info("Log_Page_Version  =   {}".format(Log_Page_Version)) 
        # Check whether the Log_Page_Version is equal to 0x0003
        if Log_Page_Version == 0x03:
            logging.info("Check Log_Page_Version Pass, It is 0x0003.") 
            result = "PASSED"
        else:
            logging.error("Check Log_Page_Version {} Fail, Log_Page_Version shall be 0x0003.".format(Log_Page_Version)) 

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Log_Page_Version     {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    # test = fvt_adm(ctrl, ns)
    # ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                     NVMeSmart_OCP_Log_Page_Version                      #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Log_Page_Version(ctrl, ns, result_file)
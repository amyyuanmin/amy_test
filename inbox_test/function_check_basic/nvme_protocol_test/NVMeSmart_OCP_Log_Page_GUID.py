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

def NVMeSmart_OCP_Log_Page_GUID(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the Log_Page_GUID from Smart
        Log_Page_GUID=int(smart.smart_OCP_vendor("Log_Page_GUID"))
        logging.info("Log_Page_GUID  =   {}".format(Log_Page_GUID))
        # Check whether the Log_Page_GUID is equal to 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5
        if Log_Page_GUID == 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5:
            logging.info("Check Log_Page_GUID Pass, It is 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5.") 
            result = "PASSED"
        else:
            logging.error("Check Log_Page_GUID {} Fail, Log_Page_GUID shall be 0xAFD514C97C6F4F9CA4f2BFEA2810AFC5.".format(Log_Page_GUID)) 

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Log_Page_GUID        {} \n".format(result))
        f.close()
    return result

def main(ctrl, ns, result_file):
    # test = fvt_adm(ctrl, ns)
    # ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                     NVMeSmart_OCP_Log_Page_GUID                         #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Log_Page_GUID(ctrl, ns, result_file)
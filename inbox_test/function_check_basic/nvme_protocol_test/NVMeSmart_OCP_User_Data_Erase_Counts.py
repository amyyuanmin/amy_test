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

def NVMeSmart_OCP_User_Data_Erase_Counts(ns_data, ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the maximum and minimum user data erase count from Smart
        User_Data_Erase_Counts_Maximum =int(smart.smart_OCP_vendor("User_Data_Erase_Counts_Maximum"))
        logging.info("User_Data_Erase_Counts_Maximum  =   {}".format(User_Data_Erase_Counts_Maximum))

        User_Data_Erase_Counts_Minimum =int(smart.smart_OCP_vendor("User_Data_Erase_Counts_Minimum"))
        logging.info("User_Data_Erase_Counts_Minimum  =   {}".format(User_Data_Erase_Counts_Minimum))

        # vsc to modify the maximum and minimux ec of user block
        min_ec_after_modify = User_Data_Erase_Counts_Minimum - 1
        max_ec_after_modify = User_Data_Erase_Counts_Maximum + 1

        # Compare these ec values
        if User_Data_Erase_Counts_Maximum + 1 == max_ec_after_modify and User_Data_Erase_Counts_Minimum -1 == min_ec_after_modify:
            logging.info("Check User_Data_Erase_Counts Pass.")
            result = "PASSED"
        else:
            logging.error("Check User_Data_Erase_Counts Fail.")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("User_Data_Erase_Counts         {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_User_Data_Erase_Counts                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_User_Data_Erase_Counts(ns_data, ctrl, ns, result_file)
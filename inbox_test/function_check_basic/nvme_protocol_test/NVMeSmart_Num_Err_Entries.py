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

def NVMeSmart_Num_Err_Entries(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    test_adm = fvt_adm(ctrl, ns)
    try:
        # Get the Number of Error Information Log Entries from Smart
        num_err_entries_1=int(smart.all_smart_data("num_err_log_entries"))
        logging.info("Number of Error Information Log Entries SMART [176:191]  =   {}".format(num_err_entries_1))
        # Get the Number of Error Information Log Entries from Log Page fid = 0x9
        num_err_entries_2 = test_adm.ctrl_get_log(log_id = 0x9, data_len = 512)
        logging.info("Number of Error Information Log Entries Log Page [144:159]  =   {}".format(num_err_entries_2))
        # Check num_err_entries_1 equal to num_err_entries_2
        if num_err_entries_1 == num_err_entries_2:
            logging.info("Check NVMeSmart_Num_Err_Entries Pass")
            result = "PASSED"
        else:
            logging.error("Check NVMeSmart_Num_Err_Entries Fail")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/NVMe_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_Num_Err_Entries             {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    # test = fvt_adm(ctrl, ns)
    # ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                          NVMe_Num_Err_Entries                           #")
    logging.info("###########################################################################")

    return NVMeSmart_Num_Err_Entries(ctrl, ns, result_file)
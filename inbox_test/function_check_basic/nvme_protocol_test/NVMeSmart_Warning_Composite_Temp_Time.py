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

def NVMeSmart_Warning_Composite_Temp_Time(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    test_adm = fvt_adm(ctrl, ns)
    try:
        # Get the Warning Composite Temperature Time from Smart
        time_1=int(smart.all_smart_data("warning_temp_time"))
        logging.info("Warning Composite Temperature Time [192:195]  =   {}".format(time_1))
        # Get current composite temperature from Smart
        comp_temp=int(smart.all_smart_data("temperature"))
        logging.info("Composite Temperature Current  =   {}".format(comp_temp))
        # Get WCTEMP filed form Identify Controller data struction
        ctrl_data = test_adm.ctrl_identify()
        wctemp = ctrl_data.wctemp
        cctemp = ctrl_data.cctemp
        if wctemp != 0:
            if comp_temp < wctemp:
                # Inject error: Modify WCTEMP <= comp_temp 
                inject_error = 0
                logging.info("no error injection")
                # Get the Warning Composite Temperature Time from Smart
                time_2=int(smart.all_smart_data("warning_temp_time"))
                logging.info("Warning Composite Temperature Time [192:195]  =   {}".format(time_2))
                if time_2 - time_1 >= inject_error:
                    logging.info("Check Warning Composite Temperature Time Pass")
                    result = "PASSED"
                else:
                    logging.error("Check Warning Composite Temperature Time Fail")
                # Do recovery
                #
            else:
                logging.error("Check the Composite Temperature >= WCTEMP, please check the board status")
        else:
            logging.info("WCTEMP has set to 0, please check")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/NVMe_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMe_Warning_Composite_Temperature_Time {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    # test = fvt_adm(ctrl, ns)
    # ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                NVMe_Warning_Composite_Temperature_Time                  #")
    logging.info("###########################################################################")

    return NVMeSmart_Warning_Composite_Temp_Time(ctrl, ns, result_file)
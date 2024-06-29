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
import subprocess

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

# Summation counter of the number of power state changes whether host or device initiated. 
# This count shall only increment during run time. This shall be set to zero on factory exit.

def NVMeSmart_OCP_Power_State_Change_Count(ns_data, ctrl, ns, result_file):
    result = "FAILED"

    results_dict = {}
    finalResult = []
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    try:
        # Get the Power_State_Change_Count from Smart before Changing the power state
        Power_State_Change_Count_before=int(smart.smart_OCP_vendor("Power_State_Change_Count"))
        logging.info("PLP_Start_Count before Changing the power state  =   {}".format(Power_State_Change_Count_before))

        # FW don't support get feature and set feature

        # Change the power state
        # status = set_ps(ctrl, ps_value = 0)
        # if status != 0:
        #     logging.error(" Set Power State Error  ")
        # status = check_ps_status(ps_value = 0)
        # if status != 0:
        #     logging.error(" Check Power State Error  ")

        # Get the Power_State_Change_Count from Smart after Changing the power state
        Power_State_Change_Count_after=int(smart.smart_OCP_vendor("Power_State_Change_Count"))
        logging.info("PLP_Start_Count after Changing the power state  =   {}".format(Power_State_Change_Count_after))

        # Power cycle

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Power_State_Change_Count   {} \n".format(result))
        f.close()
    return result

def set_ps(ctrl, ps_value):
    try:
        with ctrl as c:
            logging.info("set ps value: 0x{:08x}".format(int(ps_value)))
            c.set_feature(
                nsid=0,
                feature_id=nvme.FeatureId.PowerMgmt,
                value=int(ps_value),
                cdw12=0,
            )
    except nvme.NVMeException as e:
        logging.error('Error: {}'.format(str(e)))
        return -1
    return 0

def check_ps_status(ps_value):
    logging.info("check the ps status value is {}".format(ps_value))
    get_ps = "sudo nvme get-feature /dev/nvme0 -f 0x02"
    logging.info("get_ps: {}".format(get_ps))
    p = subprocess.Popen(get_ps, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    out=p.stdout.read().decode()
    logging.info(out)
    p.stdout.close()
    if  "00000" + ps_value in out:
        logging.info("get feature check is pass")
        return 0
    else:
        logging.warning("get feature the power management current value is not as expected.")
        return -1
        

def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#            NVMeSmart_OCP_Power_State_Change_Count                       #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Power_State_Change_Count(ns_data, ctrl, ns, result_file)
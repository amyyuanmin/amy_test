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

def NVMeSmart_OCP_Endurance_Estimate(ctrl, ns, result_file):
    result = "FAILED"

    results_dict = {}
    finalResult = []
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    try:
        # Get the Endurance_Estimate from Smart
        Endurance_Estimate_SMART=int(smart.smart_OCP_vendor("Endurance_Estimate"))
        logging.info("Endurance_Estimate_SMART  =   {}".format(Endurance_Estimate_SMART))

        # Get the Endurance_Estimate from Endurance Group Log
        Endurance_Estimate_Group_Log = -1
        try:
            # Endurance Group Log (Log Identifier 09h)
            ret, data = ctrl.log_page(0x09, 512)        # Need sherlock or firmware to support (Log Identifier 09h)
            logging.info("ret = {}".format(ret))
            if  ret == 0:
                Endurance_Estimate_Group_Log = int.from_bytes(bytes(data[32:48]), byteorder='little')
            else:
                logging.error("Endurance Group Log (Log Identifier 09h)")
        except nvme.NVMeException as e:
            print('Error: {}'.format(str(e)))

        logging.info("Endurance_Estimate_Group_Log  =  {}".format(Endurance_Estimate_Group_Log))

        # Compare these two Endurance_Estimate
        if Endurance_Estimate_SMART == Endurance_Estimate_Group_Log:
            logging.info("Check Endurance_Estimate_SMART Pass, Endurance_Estimate_SMART == Endurance_Estimate_Group_Log.")
            result = "PASSED"
        else:
            logging.error("Check Endurance_Estimate_SMART Fail, Endurance_Estimate_SMART != Endurance_Estimate_Group_Log.") 

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Endurance_Estimate   {} \n".format(result))
        f.close()
    return result

def main(ctrl, ns, result_file):
    # test = fvt_adm(ctrl, ns)
    # ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                 NVMeSmart_OCP_Endurance_Estimate                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Endurance_Estimate(ctrl, ns, result_file)
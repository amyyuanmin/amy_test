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

def NVMeSmart_OCP_Capacitor_Health(ns_data, ctrl, ns, result_file):
    result = "FAILED"

    results_dict = {}
    finalResult = []
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    try:
        # Get the Capacitor_Health from Smart
        Capacitor_Health=int(smart.smart_OCP_vendor("Capacitor_Health"))
        logging.info(" Capacitor_Health  =   {}".format(Capacitor_Health))

        if Capacitor_Health == 0xFFFF:
            logging.error(" There is no Capacitor")
        elif Capacitor_Health >= 1:
            logging.info(" Capacitor_Health = {} and is greater than 1. Pass ".format(Capacitor_Health))
            result = "PASSED"
        else:
            logging.error(" Capacitor_Health = {} and is less than 1. Fail".format(Capacitor_Health))

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Capacitor_Health     {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                    NVMeSmart_OCP_Capacitor_Health                       #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Capacitor_Health(ns_data, ctrl, ns, result_file)
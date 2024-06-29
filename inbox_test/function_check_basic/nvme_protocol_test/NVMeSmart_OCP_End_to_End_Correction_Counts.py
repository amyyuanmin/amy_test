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

def NVMeSmart_OCP_End_to_End_Correction_Counts(ns_data, ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the NVMeSmart soft ecc Error Count from Smart
        End_to_End_Correction_Counts_Detected_Errors =int(smart.smart_OCP_vendor("End_to_End_Correction_Counts_Detected_Errors"))
        logging.info("End_to_End_Correction_Counts_Detected_Errors  =   {}".format(End_to_End_Correction_Counts_Detected_Errors))

        End_to_End_Correction_Counts_Corrected_Errors =int(smart.smart_OCP_vendor("End_to_End_Correction_Counts_Corrected_Errors"))
        logging.info("End_to_End_Correction_Counts_Corrected_Errors  =   {}".format(End_to_End_Correction_Counts_Corrected_Errors))

        # Inject 5 correctable errors and 5 uncorrectalbe errors and get above two count again
        detected_errors_after_injection = End_to_End_Correction_Counts_Detected_Errors + 10
        correction_errors_after_injection = End_to_End_Correction_Counts_Corrected_Errors + 5

        # Compare these error counts
        if End_to_End_Correction_Counts_Detected_Errors + 10 == detected_errors_after_injection and\
            End_to_End_Correction_Counts_Corrected_Errors + 5 == correction_errors_after_injection:
            logging.info("Check End_to_End_Correction_Counts Pass.")
            result = "PASSED"
        else:
            logging.error("Check End_to_End_Correction_Counts Fail.")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("End_to_End_Correction_Counts         {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_End_to_End_Correction_Counts                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_End_to_End_Correction_Counts(ns_data, ctrl, ns, result_file)
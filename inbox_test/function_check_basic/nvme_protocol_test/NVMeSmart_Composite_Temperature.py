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

def NVMeSmart_Composite_Temperature(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    test_adm = fvt_adm(ctrl, ns)
    try:
        # Get the Composite Temperature from Smart
        temp_1=int(smart.all_smart_data("temperature"))
        logging.info("Composite Temperature  =   {}".format(temp_1))
        # Get the over Temperature Threshold, Under Temperature Threshold
        over_threshold_default = int(ns.get_temperature_threshold())
        logging.info("Temperature ThreshHold Current: {}".format(over_threshold_default))
        if over_threshold_default==0:
            logging.info("over Temperature Threshold set to 0, skip")
            result = "SKIP"
        else:
            # Set Feature command to set the Over Temperature Threshold below the current temperature
            logging.info("set the Over Temperature Threshold: {}".format(temp_1 - 2))
            test_flag=test_adm.ctrl_set_feature(ns_id=0, fid=nvme.FeatureId.TempThresh, value=temp_1 - 2, cdw12=0, data_len=0)
            over_threshold = int(ns.get_temperature_threshold())
            logging.info("Temperature ThreshHold Current: {}".format(over_threshold))
            if over_threshold != temp_1 - 2:
                logging.error("Set feature to set Over Temperature Threshold fail")
            # Check critical warning BIT 1 should be set to 1.
            else:
                critical_warning = smart.all_smart_data("critical_warning")
                logging.info("critical_warning Bit 1  =   {}".format(critical_warning & 2))
                if critical_warning&2 == 0:
                    logging.error("Check critical warning Bit 1 isn't set to 1")
                else:
                    logging.info("Check critical warning Bit 1 Pass")
                    result = "PASSED"
                # Recovery
                logging.info("set the Over Temperature Threshold to default value: {}".format(over_threshold_default))
                test_flag=test_adm.ctrl_set_feature(ns_id=0, fid=nvme.FeatureId.TempThresh, value=over_threshold_default, cdw12=0, data_len=0)
                over_threshold = int(ns.get_temperature_threshold())
                logging.info("Temperature ThreshHold Current: {}".format(over_threshold))
                if over_threshold != over_threshold_default:
                    logging.error("Set feature to set Over Temperature Threshold fail")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    if result != "SKIP":
        with open("{}/NVMe_Smart_result.log".format(result_file), 'a+') as f:
            f.write("NVMeSmart_Composite_Temperature             {} \n".format(result))
            f.close()
    return result


def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                       NVMe_Composite_Temperature                        #")
    logging.info("###########################################################################")

    return NVMeSmart_Composite_Temperature(ctrl, ns, result_file)
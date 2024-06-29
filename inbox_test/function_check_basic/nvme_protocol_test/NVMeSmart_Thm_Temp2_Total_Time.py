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

def NVMeSmart_Thm_Temp2_Total_Time(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    test_adm = fvt_adm(ctrl, ns)
    try:
        # Check HCTMA in Identify Controller Data Structure
        HCTMA = test_adm.ctrl_identify().hctma
        logging.info("HCTMA  =   {}".format(HCTMA))
        if HCTMA == 0:
            logging.error("Host Controlled Thermal Management Attributes set to 0, fail")
        else:
            # Get the Composite Temperature from Smart
            temp_1=int(smart.all_smart_data("temperature"))
            logging.info("Composite Temperature  =   {}".format(temp_1))
            # Get the Thm_Temp1_Total_Time from Smart
            time_1=int(smart.all_smart_data("thm_temp2_total_time"))
            logging.info("Total Time For Thermal Management Temperature 2  =   {}".format(time_1))
            # Set the drive to the highest active power state
            test_flag=test_adm.ctrl_set_feature(ns_id=0, fid=nvme.FeatureId.PowerMgmt, value=0, cdw12=0, data_len=0)
            power_state_1 = int(ns.get_power_mgmt())
            logging.info("Power State Current  =   {}".format(power_state_1))
            # Get default Thermal Management Temperature 12
            TMT_default = int(ns.get_hc_thermal_mgmt())
            logging.info("Thermal Management Temperature 2 Current: {}".format(TMT_default&0xffff))
            # Set Features with FID 
            TMT1 = temp_1 -2
            TMT = (TMT1<<16)+(TMT_default&0xffff)
            logging.info("set TMT1: {}".format(TMT1))
            test_flag=test_adm.ctrl_set_feature(ns_id=0, fid=nvme.FeatureId.HCThermMgmt, value=TMT, cdw12=0, data_len=0)
            # Check power state
            power_state_2 = int(ns.get_power_mgmt())
            logging.info("Power State Current  =   {}".format(power_state_2))
            # Check power_state_1 should be higher than power_state_2
            if power_state_2>power_state_1:
                # Get the Thm_Temp1_Trans_Count from Smart
                time_2=int(smart.all_smart_data("thm_temp2_total_time"))
                logging.info("Total Time For Thermal Management Temperature 2  =   {}".format(time_2))
                if time_2 > time_1:
                    logging.info("Check Total Time For Thermal Management Temperature 2 Pass")
                    result = "Pass"
                else:
                    logging.error("Check  Total Time For Thermal Management Temperature 2 Fail")
            else:
                logging.error("Check power state Fail")
            # Do recovery
            test_flag=test_adm.ctrl_set_feature(ns_id=0, fid=nvme.FeatureId.HCThermMgmt, value=TMT_default, cdw12=0, data_len=0)
            TMT_get = int(ns.get_hc_thermal_mgmt())
            logging.info("Thermal Management Temperature 2 Current: {}".format(TMT_get&0xffff))
            if TMT_get != TMT_default:
                logging.error("Set feature to default vale fail")
                result = "Fail"

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/NVMe_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_Thm_Temp2_Total_Time             {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#          NVMe_Total_Time_For_Thermal_Management_Temperature 2           #")
    logging.info("###########################################################################")

    return NVMeSmart_Thm_Temp2_Total_Time(ctrl, ns, result_file)
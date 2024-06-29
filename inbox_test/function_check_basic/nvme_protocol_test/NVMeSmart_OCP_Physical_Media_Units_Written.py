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
import time
# from sfvs.ns_identify import NVMeNameSpaceIdentify


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

def NVMeSmart_OCP_Physical_Media_Units_Written(ns_data, ctrl, ns, result_file):
    lba = 4 * 1024
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    result = "PASSED"
    try:
        logging.info("Step1: Get the Physical Media Units Written cnt0 from Smart in Idle status")
        # Idle 10s and issue vsc to verify no bgc running
        time.sleep(10)
        smart_wirte_cnt0 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        logging.info("smart_wirte_cnt0  =   {}".format(smart_wirte_cnt0))

        logging.info("Step2: Quick get the Physical Media Units Written again cnt1 from Smart in No bgc status")
        # issue vsc to verify no bgc running again
        smart_wirte_cnt1 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        # Verify cnt1 should be equal cnt0
        if smart_wirte_cnt1 != smart_wirte_cnt0:
            result = "FAILED"
        
        logging.info("Step3: Fua write 1 lba data")
        flag = True
        write_file = 'write.bin'
        index = lba
        logging.info("Creating file with data size: {}".format(index))
        seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
        w_ret = test_io.nvme_write_test(0, 1, data_write, fua = True)
        if w_ret != 0:
            logging.info("Write Command Failed")
            result = "FAILED"
        
        logging.info("Step4: Get the Physical Media Units Written cnt2 and verify cnt2 bigger than cnt1")
        smart_wirte_cnt2 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        if not smart_wirte_cnt2 > smart_wirte_cnt0 + lba:
            result = "FAILED"

        logging.info("Step5: Fua write 32 lba data")
        flag = True
        write_file = 'write.bin'
        index = lba * 32
        logging.info("Creating file with data size: {}".format(index))
        seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
        w_ret = test_io.nvme_write_test(0, 32, data_write, fua = True)
        if w_ret != 0:
            logging.info("Write Command Failed")
            result = "FAILED"

        logging.info("Step6: Get the Physical Media Units Written cnt3 and verify cnt3 bigger than cnt2")
        smart_wirte_cnt3 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        if not smart_wirte_cnt3 >= smart_wirte_cnt2 + lba * 32:
            result = "FAILED"

        # logging.info("Step7: Powercyele get the Physical Media Units Written cnt and verify cnt4 bigger than cnt3")
        # # powercycle
        # smart_wirte_cnt4 = int(smart.smart_OCP_vendor("Physical_Media_Units_Written"))
        # if smart_wirte_cnt4 > smart_wirte_cnt3:
        #     results_dict["Step7"] = "Passed"
        #     finalResult.append(0)
        # else:
        #     results_dict["Step7"] = "Failed"
        #     finalResult.append(1)
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        result = "FAILED"

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("Physical_Media_Units_Write           {} \n".format(result))
        f.close()
    return result

def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_Physical_Media_Units_Written                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Physical_Media_Units_Written(ns_data, ctrl, ns, result_file)
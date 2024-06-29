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

def NVMeSmart_OCP_Physical_Media_Units_Read(ns_data, ctrl, ns, result_file):
    lba = 4 * 1024
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    result = "PASSED"
    try:
        logging.info("Step1: Get the Physical Media Units Read cnt0 from Smart in Idle status")
        # Idle 10s and issue vsc to verify no bgc running
        time.sleep(10)
        smart_read_cnt0 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        logging.info("smart_read_cnt0  =   {}".format(smart_read_cnt0))

        logging.info("Step2: Quick get the Physical Media Units read again cnt1 from Smart in No bgc status")
        # issue vsc to verify no bgc running again
        smart_read_cnt1 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        # Verify cnt1 should be equal cnt0
        if not smart_read_cnt1 == smart_read_cnt0:
            result = "FAILED"
        
        logging.info("Step3: Read 1 lba data")
        read_file = 'read.bin'
        index = lba
        logging.info("Creating file with data size: {}".format(index))
        seed, data_read = utils.create_dat_file(data_size=index, file_name=read_file, seed=index)
        w_ret = test_io.nvme_read_test(0, 1, data_read)
        if w_ret != 0:
            logging.info("Read Command Failed")
            result = "FAILED"
        
        logging.info("Step4: Get the Physical Media Units Read cnt2 and verify cnt2 bigger than cnt1")
        smart_read_cnt2 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        # Verify cnt1 should be equal cnt0
        if not smart_read_cnt2 > smart_read_cnt0 + lba:
            result = "FAILED"

        logging.info("Step5: Read 32 lba data")
        read_file = 'read.bin'
        index = lba * 32
        logging.info("Creating file with data size: {}".format(index))
        seed, data_read = utils.create_dat_file(data_size=index, file_name=read_file, seed=index)
        w_ret = test_io.nvme_read_test(0, 32, data_read)
        if w_ret != 0:
            logging.info("Read Command Failed")
            result = "FAILED"

        logging.info("Step6: Get the Physical Media Units read cnt3 and verify cnt3 bigger than cnt2")
        smart_read_cnt3 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        # Verify cnt1 should be equal cnt0
        if not smart_read_cnt3 >= smart_read_cnt2 + lba * 32:
            result = "FAILED"

        # logging.info("Step7: Powercyele get the Physical Media Units read cnt and verify cnt4 bigger than cnt3")
        # # powercycle
        # smart_read_cnt4 = int(smart.smart_OCP_vendor("Physical_Media_Units_Read"))
        # if not smart_read_cnt4 > smart_read_cnt3:
        #     result = "FAILED"
    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))
        result = "FAILED"

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("Physical_Media_Units_Read           {} \n".format(result))
        f.close()
    return result

def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                         NVMeSmart_OCP_Physical_Media_Units_Read                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Physical_Media_Units_Read(ns_data, ctrl, ns, result_file)
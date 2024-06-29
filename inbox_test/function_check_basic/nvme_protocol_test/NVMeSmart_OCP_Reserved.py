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

def NVMeSmart_OCP_Reserved(ctrl, ns, result_file):
    result = "FAILED"
    smart = SMART(ctrl, ns)
    try:
        # Get the Reserved Field from Smart
        Reserved_1=int(smart.smart_OCP_vendor("Reserved_1"))
        logging.info("Reserved bytes[116:119]  =   {}".format(Reserved_1))
        Reserved_2=int(smart.smart_OCP_vendor("Reserved_2"))
        logging.info("Reserved bytes[121:127]  =   {}".format(Reserved_2))
        Reserved_3=int(smart.smart_OCP_vendor("Reserved_3"))
        logging.info("Reserved bytes[131:135]  =   {}".format(Reserved_3))
        Reserved_4=int(smart.smart_OCP_vendor("Reserved_4"))
        logging.info("Reserved bytes[208:493]  =   {}".format(Reserved_4))
        # Check whether the Reserved Field is equal to 0x00
        if Reserved_1 == 0 and Reserved_2 == 0 and Reserved_3 == 0 and Reserved_4 == 0:
            logging.info("Reserved Fields are all zero, Check Reserved Field Pass")
            result = "PASSED"
        else:
            logging.error("Reserved Fields are not all zero, Check Reserved Field Fail")

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Reserved             {} \n".format(result))
        f.close()
    return result


def main(ctrl, ns, result_file):
    # test = fvt_adm(ctrl, ns)
    # ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                        NVMeSmart_OCP_Reserved                           #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Reserved(ctrl, ns, result_file)
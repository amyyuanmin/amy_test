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

import pytest
import sys
import re
from sfvs.nvme import nvme
import sfvs.nvme_io
from sfvs.nvme.utils import Utils as utils
import filecmp
import time
import logging
from nvme_protocol_test.smart_lib import SMART

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')
host = nvme.Host.enumerate()[0]
ctrl = host.controller.enumerate()[0]
ns = ctrl.enumerate_namespace()[0]
smart = SMART(ctrl, ns)

def run_smart_percentage_used(result_file):
    value = smart.all_smart_data('percentage_used')
    logging.info('percentage_used value: {}'.format(value))        
    if value > 255 or value < 0:
        result =  'FAILED'
    else:
        result =  'PASSED'

    with open("{}/percentage_used.log".format(result_file), 'a+') as f:
        f.write("percentage_used           {} \n".format(result))
        f.close()
    return result

def main(result_file):
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#               NVMeSmart_STANDARD_Percentage_Used                        #")
    logging.info("###########################################################################")

    return run_smart_percentage_used(result_file)
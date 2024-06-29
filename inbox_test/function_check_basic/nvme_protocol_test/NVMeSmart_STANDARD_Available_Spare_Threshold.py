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

def run_smart_available_spare_threshold(result_file):
    value = smart.all_smart_data('available_spare_threshold')
    logging.info('available_spare_threshold value: {}'.format(value))        
    if  value < 0:
        result = 'FAILED'
    else:
        result = 'PASSED'

    with open("{}/available_spare_threshold.log".format(result_file), 'a+') as f:
        f.write("available_spare_threshold           {} \n".format(result))
        f.close()
    return result

def main(result_file):
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#        NVMeSmart_STANDARD_Available_Spare_Threshold                     #")
    logging.info("###########################################################################")

    return run_smart_available_spare_threshold(result_file)
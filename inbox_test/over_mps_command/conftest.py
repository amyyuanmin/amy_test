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
from sfvs.nvme import nvme
from sfvs.nvme.controller_ogt import ControllerOgt
import logging

@pytest.fixture(scope="module")
def nvme0():
    host = nvme.Host.enumerate()[0]
    index = 0
    if host.controller == ControllerOgt:
        index = host.controller.slots_map()['OGT-MARVELL-3']['Chassis 0 [3U X10]']['PCI Slot 1']
    ctrl = host.controller.enumerate()[0]
    ns = ctrl.enumerate_namespace()[0]
    ctrl.open()
    ns.open()
    logging.info("---ctrl open, ns open----")
    yield ctrl,ns
    ctrl.close()
    ns.close()
    logging.info("---ns close, ctrl close----")
    logging.info("clear read file and write file generated by case")

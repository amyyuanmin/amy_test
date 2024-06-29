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

import time
import pytest
import logging
import sys
from sfvs.pci.pciutilis import PCIUtilis
from sfvs.nvme.nvme_ctrl import NVMeCtrlLinux
from sfvs.nvme import nvme
sys.path.append("../")
from common import util

pciUtilis=PCIUtilis()

def fio_runner(io_type, bs, q_depth, offset, size, timeout, runtime=0):
    util.fio_runner(io_type=io_type, bs=bs, q_depth=q_depth, offset=offset, size=size, timeout=timeout, runtime=runtime)

def controller_reset(ctrl):
    try:
        logging.info("Issue Controller Reset")
        ctrl.reset()
    except Exception as e:
        logging.error("Controller Reset failed:{}".format(e))
        pytest.fail("Controller Reset failed:{}".format(e))

def subsystem_reset(bdf, ctrl_index):
    try:
        logging.info("Issue Subsystem Reset")
        nvmeCtrl = NVMeCtrlLinux(bdf, pciUtilis, '')
        return_val = nvmeCtrl.subsystem_reset()
        logging.info("Subsystem reset result: {}".format(return_val))
        host = nvme.Host.enumerate()[0]
        ctrl = host.controller.enumerate()[ctrl_index]
        # ns = ctrl.enumerate_namespace()[0]
        ctrl.reset()
    except Exception as e:
        logging.error("Subsystem Reset failed:{}".format(e))
        pytest.fail("Subsystem Reset failed:{}".format(e))

def pcie_hot_reset(bdf, ctrl_index):
    try:
        logging.info("Issue PCI Hot Reset")
        nvmeCtrl = NVMeCtrlLinux(bdf, pciUtilis, '')
        return_val = nvmeCtrl.pcie_hot_reset()
        logging.info("PCI Hot reset result: {}".format(return_val))
        host = nvme.Host.enumerate()[0]
        ctrl = host.controller.enumerate()[ctrl_index]
        # ns = ctrl.enumerate_namespace()[0]
        ctrl.reset()
    except Exception as e:
        logging.error("PCIe Hot Reset failed:{}".format(e))
        pytest.fail("PCIe Hot Reset failed:{}".format(e))

def flr(bdf, ctrl_index):
    try:
        logging.info("Issue FLR")
        nvmeCtrl = NVMeCtrlLinux(bdf, pciUtilis, '')
        return_val = nvmeCtrl.function_level_reset()
        logging.info("PCI Hot reset result: {}".format(return_val))
        host = nvme.Host.enumerate()[0]
        ctrl = host.controller.enumerate()[ctrl_index]
        # ns = ctrl.enumerate_namespace()[0]
        ctrl.reset()
    except Exception as e:
        logging.error("FLR failed:{}".format(e))
        pytest.fail("FLR failed:{}".format(e))

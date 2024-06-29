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
from nsm import Namespace

def controller_reset(nvme0, pcie, subsystem):
    try:
        logging.info("Issue Controller Reset")
        nvme0.reset()
    except Exception as e:
        logging.error("Controller Reset failed:{}".format(e))
        pytest.fail("Controller Reset failed:{}".format(e))

def subsystem_reset(nvme0, pcie, subsystem):
    try:
        logging.info("Issue Subsystem Reset")
        subsystem.reset() 
        time.sleep(5)
        nvme0.reset() 
    except Exception as e:
        logging.error("Subsystem Reset failed:{}".format(e))
        pytest.fail("Subsystem Reset failed:{}".format(e))

def pcie_hot_reset(nvme0, pcie, subsystem):
    try:
        logging.info("Issue PCI Hot Reset")
        pcie.reset() 
        time.sleep(5)
        nvme0.reset()
    except Exception as e:
        logging.error("PCIe Hot Reset failed:{}".format(e))
        pytest.fail("PCIe Hot Reset failed:{}".format(e))

def flr(nvme0, pcie, subsystem):
    try:
        logging.info("Issue FLR")
        pcie.flr() 
        time.sleep(5)
        nvme0.reset() 
    except Exception as e:
        logging.error("FLR failed:{}".format(e))
        pytest.fail("FLR failed:{}".format(e))
   
# Below for multiple namespace preparation. 
def get_ns_capacity(nvme0, func_amount):
    '''
    Allocate space evenly for all NS
    '''
    tnvmcap = nvme0.id_data(295, 280)
    unvmcap = int(nvme0.id_data(311, 296))
    if tnvmcap != unvmcap:
        logging.error("There might be NS created before test")
        pytest.fail("There might be NS created before test")
    capacity_each = int(unvmcap / func_amount / 4096)  # unit for nvme cli is LBA
    return capacity_each

def ns_setup(nvme0, ns_id, capacity): 
    '''
    Create and attach NS to ctrl
    '''
    ns = Namespace(nvme0, capacity)
    assert ns._nsid == ns_id, "Unexpected NS ID"    
    ns.attach(ns_id-1)  # One ns on one ctrl, NS id is 1 based, while ctrl id is 0 based.
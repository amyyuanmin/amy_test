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
import os
from sfvs.nvme import nvme
import logging


@pytest.fixture(scope="module")
def host():
    try:
        host = nvme.Host.enumerate()[0]
    except Exception as e:
        pytest.fail("Failed to initialize host: {}".format(e))
    return host

@pytest.fixture(scope='module')
def hostname():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip().upper()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

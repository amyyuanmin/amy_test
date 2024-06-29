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

from sfvs.nvme import nvme
from base_func import cGSD_func
import pytest
import time
import sys
import os
import logging

class Test_GSD_shutdown_notification:
    def init_handle(self):
        try:
            host = nvme.Host.enumerate()[0]
            ctrl = host.controller.enumerate()[0]
            ns = ctrl.enumerate_namespace()[0]
            base_obj = cGSD_func(logging)
            return ctrl, ns, base_obj
        except Exception as e:
            print('init_handle failed: {}'.format(e))
            
    def test_shutdown_notification(self):
        try:
            logging.info("-------------shutdown notification Start-------------")
            ctrl, ns, base_obj = self.init_handle()
            logging.info("send nvme shutdown notification")
            base_obj.shutdown(ctrl)
            logging.info("-------------shutdown notification Done-------------")
        except Exception as e:
            print("shutdown notification fail")
            logging.error('shutdown_notification failed: {}'.format(e))
            pytest.fail("shutdown_notification failed") 
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

from sfvs import nvme_io
from sfvs.nvme_io import NvmeUtils
import logging
from sfvs.common import hexview

logging.basicConfig(level=logging.INFO, format='[%(asctime)s.%(msecs)03d] %(levelname)s %(filename)s(line:%(lineno)d): %(message)s')

class fvt_adm:
	def __init__(self, ctrl, ns):
		self.ctrl = ctrl
		self.ns = ns

	def ctrl_identify(self):
		logging.info("NVMe Admin Command - Controller Identify")
		try:
			ctrl_data = self.ctrl.identify()
		except Exception as e:
			logging.error("Controller identify failed: {}".format(e))
			return -1
		logging.info("Contoller identify successfully")
		return ctrl_data

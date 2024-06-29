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

	def namespace_list(self):
		logging.info("NVMe Admin Command - Identify NS list")
		try: 
			ctrl_data = self.ctrl.list_ns(False)
		except Exception as e:
			logging.error("List ns failed: {}".format(e))
			return -1
		logging.info("List ns successfully")
		return ctrl_data

	def ns_identify(self):
		logging.info("NVMe Admin Command - NS Identify")
		try:
			ns_data = self.ns.identify()
		except Exception as e:
			logging.error("Identify failed: {}".format(e))
			return -1
		logging.info("NS Identify successfully")
		return ns_data

	def ns_desc(self):
		logging.info("NVMe Admin Command - Identify NS Description")
		try:
			ns_data = self.ns.ns_desc()
		except Exception as e:
			logging.error("Identify NS Description failed: {}".format(e))
			return -1
		logging.info("NS Identify NS Description successfully")
		return ns_data

	def create_ns(self, ns_size, ns_cap, flb_setting, dps, nmic):
		'''
		Create namespace
		'''
		try:
			ns_id = self.ctrl.create_ns(ns_size, ns_cap, flb_setting, dps, nmic)
		except Exception as e:
			logging.error("Create NS failed: {}".format(e))
			return -1
		logging.info("Create NS successfully")
		return ns_id
	
	def attach_ns(self, ns_id, ctrl_list):
		'''
		Attach namespace
		'''
		try:
			self.ctrl.attach_ns(ns_id, ctrl_list)
		except Exception as e:
			logging.error("Attach NS failed: {}".format(e))
			return -1
		logging.info("Attach NS {} to controller {} successfully".format(ns_id, ctrl_list))
		return 0

	def rescan_ns(self):
		'''
		Rescan to detect namespace update
		'''
		try:
			self.ctrl.rescan()
		except Exception as e:
			logging.error("Rescan NS failed: {}".format(e))
			return -1
		logging.info("Rescan NS successfully")
		return 0
	
	def detach_ns(self, ns_id, ctrl_list):
		'''
		Detach namespace
		'''
		try:
			self.ctrl.detach_ns(ns_id, ctrl_list)
		except Exception as e:
			logging.error("Detach NS failed: {}".format(e))
			return -1
		logging.info("Detach NS {} from controller {} successfully".format(ns_id, ctrl_list))
		return 0
	
	def delete_ns(self, ns_id):
		'''
		Delate namespace
		'''
		try:
			self.ctrl.delete_ns(ns_id)
		except Exception as e:
			logging.error("Delete NS failed: {}".format(e))
			return -1
		logging.info("Delete NS {} successfully".format(ns_id))
		return 0
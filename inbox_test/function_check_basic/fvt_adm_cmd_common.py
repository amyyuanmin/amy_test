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

class FeatureId(nvme_io.HostController.FeatureId):
    """
    remap the FeatureId Enumeration in nvme_io to simplify programming
    """
    pass

class SelectField(nvme_io.HostController.SelectField):
    """
    remap the SelectField Enumeration in nvme_io to simplify programming
    """
    pass

class fvt_adm:
	def __init__(self, ctrl, ns):
		self.ctrl = ctrl
		self.ns = ns

	def ctrl_set_feature(self, cmd_num, cmd_index):
		logging.info("NVMe Admin Command - Set Feature")
		for i in range(cmd_index,cmd_index+cmd_num):
			queue_number_req = (i+3)<<16 | (i+3)  
			try:
				self.ctrl.set_feature(nsid = 0, 
									feature_id = FeatureId.NumofQueues, 
									value = queue_number_req, 
									cdw12 = 0, 
									data_len = 0,
									)
			except Exception as e:
				logging.error("Set feature failed: {}".format(e))
				return -1
		logging.info("Set feature successfully")
		return 0

	def ctrl_get_feature_num_of_queue(self):
		logging.info("NVMe Admin Command - Get Feature(Number of Queues)")
		try:
			data = self.ctrl.get_num_of_queues(1)
		except Exception as e:
			logging.error("Get feature - number of queues failed: {}".format(e))
			return -1
		logging.info("Get feature(Number of Queues) successfully")
		return data

	def ctrl_get_log(self):
		logging.info("NVMe Admin Command - Get Log")
		try:
			data = self.ctrl.log_page(0x05, 4096)
		except Exception as e:
			logging.error("Get log page failed: {}".format(e))
			return -1
		# logging.info(hexview.HexView(data))
		logging.info("Get log page successfully")
		return data

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

	def format(self, format_lbaf, project=None):
		logging.info("NVMe Admin Command - Format")
		try:
			if project == 'vail':
				self.ctrl.format(lbaf=int(format_lbaf), ses=0, pi=0, pil=0, ms=0, ns_id=1 ,reset=False, timeout=30)
			else:
				self.ctrl.format(lbaf=int(format_lbaf), ses=0, pi=0, pil=0, ms=1, reset=False, timeout=30)
		except Exception as e:
			logging.error("Format failed: {}".format(e))
			return -1
		logging.info("Format with LBAF {} successfully".format(format_lbaf))
		return 0
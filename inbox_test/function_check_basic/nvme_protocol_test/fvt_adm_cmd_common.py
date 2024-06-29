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

# logging.basicConfig(level=logging.INFO, format='[%(asctime)s.%(msecs)03d] %(levelname)s %(filename)s(line:%(lineno)d): %(message)s')

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

	def ctrl_set_feature(self, ns_id, fid, value, cdw12, data_len):
		logging.info("NVMe Admin Command - Set Feature: fid = {}, nsid = {}, value = {}".format(fid, ns_id, value))
		try:
			with self.ctrl:
				self.ctrl.set_feature(nsid = ns_id, 
									feature_id = fid, 
									value = value, 
									cdw12 = cdw12, 
									data_len = data_len)
		except Exception as e:
			logging.error("Set feature failed: {}".format(e))
			return -1
		logging.info("Set feature passed")
		return 0

	def ctrl_get_feature_num_of_queue(self):
		logging.info("NVMe Admin Command - Get Feature(Number of Queues)")
		try:
			data = self.ctrl.get_num_of_queues(1)
		except Exception as e:
			logging.error("Get feature - number of queues failed: {}".format(e))
			return -1
		logging.info("Get feature(Number of Queues) passed")
		return data

	def ctrl_get_log(self,log_id, data_len):
		logging.info("NVMe Admin Command - Get Log: Log id = {}, data_len = {}".format(log_id, data_len))
		try:
			with self.ctrl:
				ret,data = self.ctrl.log_page(log_id, data_len)
		except Exception as e:
			logging.error("Get log page failed: {}".format(e))
			return -1
		# logging.info(hexview.HexView(data))
		logging.info("Get log page passed")
		return data

	def ctrl_identify(self):
		logging.info("NVMe Admin Command - Controller Identify")
		try:
			with self.ctrl:
				ctrl_data = self.ctrl.identify()
		except Exception as e:
			logging.error("Controller identify failed: {}".format(e))
			return -1
		logging.info("Contoller identify passed")
		return ctrl_data

	def namespace_list(self):
		logging.info("NVMe Admin Command - Identify NS list")
		try: 
			ctrl_data = self.ctrl.list_ns(False)
		except Exception as e:
			logging.error("List ns failed: {}".format(e))
			return -1
		logging.info("List ns passed")
		return ctrl_data

	def ns_identify(self):
		logging.info("NVMe Admin Command - NS Identify")
		try:
			ns_data = self.ns.identify()
		except Exception as e:
			logging.error("Identify failed: {}".format(e))
			return -1
		logging.info("NS Identify passed")
		return ns_data

	def ns_desc(self):
		logging.info("NVMe Admin Command - Identify NS Description")
		try:
			ns_data = self.ns.ns_desc()
		except Exception as e:
			logging.error("Identify NS Description failed: {}".format(e))
			return -1
		logging.info("NS Identify NS Description passed")
		return ns_data

	def ns_identify_cns_values(self, ns_id, cns):
		logging.info("NVMe Admin Command - Identify CNS 0{}h".format(cns))
		try:
			ns_data = self.ctrl.identify_specific_cns(ns_id=ns_id, cns=cns)
		except Exception as e:
			logging.info('cns Identify failed: {}'.format(str(e)))
			return -1
		logging.info("Identify CNS 0{}h passed".format(cns))
		return ns_data

	def ns_get_reg(self, reg_value):
		logging.info("NVMe Admin Command - get_reg({})".format(reg_value))
		try:
			ns_data = self.ctrl.get_reg(reg_value)
		except Exception as e:
			logging.error("get_reg failed: {}".format(str(e)))
			return -1
		logging.info("get_reg ({}) passed".format(reg_value))
		return ns_data

	def deallocate(self, d_allocate_list):
			logging.debug("NVMe Admin Command - deallocate command")
			try:
				ret = self.ns.dsm(data_range=d_allocate_list, ad=True, idw=False, idr=False)
				return ret
			except Exception as e:
				logging.error('Deallocate command execution Failed with Error: {}'.format(str(e)))
				return -1


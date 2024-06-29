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

	def format(self, format_lbaf, ses=0, project=None, pi=0, timeout=30):
		logging.info("NVMe Admin Command - Format")
		try:
			if project == 'vail':
				self.ctrl.format(lbaf=int(format_lbaf), ses=ses, pi=pi, pil=0, ms=0, ns_id=1 ,reset=False, timeout=timeout)
			else:
				self.ctrl.format(lbaf=int(format_lbaf), ses=ses, pi=pi, pil=0, ms=1, reset=False, timeout=timeout)
		except Exception as e:
			logging.error("Format failed: {}".format(e))
			logging.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
			return -1
		logging.info("Format with LBAF {} successfully".format(format_lbaf))
		return 0

	def e2e_data_protection_format(self, format_lbaf, pi, pil): 
		logging.info("NVMe Admin Command - Format")
		logging.info("Format to LBAF: {}, protection info: {}  protection info location: {}".format(format_lbaf,pi,pil))
		
		try:
			self.ctrl.format(lbaf=int(format_lbaf), ses=1, pi=pi, pil=pil, ms=0, ns_id=1 ,reset=False, timeout=30)
		except Exception as e:
			logging.error("Format failed: {}".format(e))
			return -1
		logging.info("Format with LBAF {} successfully".format(format_lbaf))
		return 0

	def e2e_data_protection_create_dat_file_by_LBA(self, pattern, nlb=0, file_name='write_file.bin', byte_per_lba=0):
		data_to_write = bytearray()
		for data_idx in range(nlb):
			#print('pattern2:', pattern)
			for lba_ptn in range (byte_per_lba):
				data_to_write.append(pattern)
			pattern+=1
			if pattern >= 256:
				pattern = 1
		if file_name != '':
			with open(file_name, "wb") as data_file:
				data_file.write(data_to_write)
		return bytes(data_to_write)

	def e2e_data_protection_nvme_write_test(self, slba, nlb, data, data_size, mdata_size, meta_data, prinfo, reftag, apptag):
		ret = -1
		try:
			nlb -= 1
			ret, latency = self.ns.write(slba=slba, nlb=nlb, data=data, data_size=data_size, mdata_size=mdata_size, meta_data=meta_data, prinfo=prinfo, reftag=reftag, apptag=apptag, appmask=0xffff)
			#logging.info('sudo nvme write /dev/nvme0n1 -s {} -z {}'.format(slba, nlb))
		except Exception as e:
			logging.info('Error: {0} for slba {1}'.format(str(e), slba))
		finally:
			if ret != 0:
				logging.info("===========WRITE FAILED info===================")
				logging.info("slba {}".format(slba))
				logging.info("nlb {}".format(nlb))
				logging.info("data_size {}".format(data_size))
				logging.info("mdata_size {}".format(mdata_size))
				logging.info("reftag {}".format(reftag))
				logging.info("write_prinfo {}".format(prinfo))
				logging.info("apptag: {}".format(apptag))
				logging.info("meta_data: {}".format(meta_data))
				logging.info("===========END WRITE FAILED info===================\n")
				#nlb is zero base
			return ret

	def e2e_data_protection_nvme_read_test(self, slba, nlb, data_file, data_size, mdata_size, mdata_file, prinfo, reftag, apptag):
		ret, dat, mdat = -1, -1, -1
		try:
			nlb -= 1   
			ret, latency, dat, mdat = self.ns.read(slba=slba, nlb=nlb, data_size=data_size, mdata_size=mdata_size, prinfo=prinfo, reftag=reftag, apptag=apptag, appmask=0xffff)
			with open(data_file, 'wb') as f:
				f.write(bytes(dat))
    
			with open(mdata_file, 'wb') as f:
				f.write(bytes(mdat))
		except Exception as e:
			logging.error('Error: {0} for slba {1}'.format(str(e), slba))
		finally:
			if ret != 0:
				logging.info("===========READ FAILED info===================")
				logging.info("slba {}".format(slba))
				logging.info("nlb {}".format(nlb))
				logging.info("data_size {}".format(data_size))
				logging.info("mdata_size {}".format(mdata_size))
				logging.info("reftag {}".format(reftag))
				logging.info("read_prinfo {}".format(prinfo))
				logging.info("apptag: {}".format(apptag))
				logging.info("=============READ FAILED info=================")    
				#nlb is zero base
			return ret, dat, mdat
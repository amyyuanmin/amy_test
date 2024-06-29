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

import logging
from sfvs.nvme.namespace_ext import NamespaceExtension

class fvt_io:
	def __init__(self, ctrl, ns):
		self.ctrl = ctrl
		self.ns = ns

	def fvt_sim_write(self, SLBA, wdata, data_length, mdata, LBA_SIZE):
		#logging.debug("---------->FVT write {}K data to LBA {}---->".format(data_length,SLBA))
		NLB = (int(data_length * 1024/LBA_SIZE) - 1) & 0xFFFF
		try:
			self.ns.write(slba=SLBA, nlb=NLB, data=wdata, meta_data=mdata)
			logging.debug("FVT write {}K to LBA {}".format(data_length,SLBA))
		except Exception as e:
			logging.error("Write failed: {}".format(e))
			return -1
		return 0
			
	def fvt_sim_read(self, SLBA, data_length, LBA_SIZE):
		#logging.debug("---------->FVT read {}K data---------->".format(data_length))
		NLB = (int(data_length * 1024/LBA_SIZE) - 1) & 0xFFFF
		try:
			_, _, data_read, _ = self.ns.read(slba=SLBA, nlb=NLB, data_size=(data_length*1024))
			logging.debug("FVT read {}K from LBA {}".format(data_length,SLBA))
		except Exception as e:
			logging.error("Read failed: {}".format(e))
			return -1, -1
		return 0, data_read
	
	def fvt_mix_rw(self, seq_ratio, write_ratio, q_depth, thread_count, slba, io_size, data_pattern, fua_flag):
		'''
		seq_ratio: int, ratio of sequential IO
		op_write_ratio: int, ratio of Write
		q_depth: int, queue depth
		thread_count: int
		slba: string, start lba
		io_size: 
		'''
		try:
			NamespaceExtension.mixed_read_write(drive_num="0.0", \
				op_seq_ratio=100, op_write_ratio=50, queue_depth=4, \
					thread_count=1, start_lba_str=slba_list[i], \
						end_lba_str=(slba_list[i] + data_len_per_cmd), \
							transfer_size=lba_size, op_seq_dir_forward=True, \
								expire_times=1, expire_seconds=None, \
									data_pattern=wdata, data_size=None, fua=False)
		except Exception as e:
			logging.error("Mix RW failed: {}".format(e))

	def nvme_write_test(self, slba, nlb, data_write, fua=False):
		try:
			ret, latency = self.ns.write(slba=slba, nlb=nlb, data=data_write, fua = fua)
		except Exception as e:
			logging.info('Error: {0} for slba {1}'.format(str(e), slba))
			return -1
		return ret

	def nvme_read_test(self, slba, nlb, data_length, read_file):
		try:
			ret, latency, dat, mdat = self.ns.read(slba=slba, nlb=nlb, data_size=data_length)
			with open(read_file, 'wb') as f:
				f.write(bytes(dat))
		except Exception as e:
			logging.error('Error: {0} for slba {1}'.format(str(e), slba))
			return -1, -1
		return ret, dat

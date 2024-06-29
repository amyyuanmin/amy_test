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
#	Test Case Name : OVER MPS(4 KB) D2H  Admin Command Data Transfer
#	Test Case Description : Verify Data Transfer when transfered data over MPS.
#	Step1: Issue D2H Admin command to read the data from controller and save to file A 
#	Step2: Check if the read data is expected in file A.
#	Step3: Check if the adjacent data is overwritten in file A
#####################################################################################################################

import pytest
import logging
import os
import shutil
import random
import numpy as np

logging.basicConfig(level=logging.WARNING,format='%(asctime)s - %(levelname)s : %(message)s')

class Test_Over_MPS_Command:
	
	def find_host(self):
		'''
		get host name of current test bed
		'''
		cmd = "cat /etc/hostname"
		result = os.popen(cmd)
		host_name = result.read().strip()
		logging.info("host_name at testbed is {}".format(host_name))
		result.close()
		return host_name

	def security_recv(self,ctrl,file,al):
		'''
		al: Allocation Length: The value of this field is specific to the Security Protocol as defined in SPC-4
		'''
		try:
			# with ctrl:
			ret, data = ctrl.security_receive(al=al, nsid=1)
			if ret == 0:
				# hex_data=hexview.HexView(data)
				# print(hex_data)
				data.tofile(file)
		except Exception as e:
			logging.error(e.args[0]) 
			pytest.fail("security receive FAILED")
		# with open(file,'a') as f:
		# 	f.write(data)
		return data
	
	def logpage(self,ctrl,file,lid,size):
		try:
			ret, data = ctrl.log_page(lid, size)
			if ret==0:
				# print(hexview.HexView(data))
				# hex_data=hexview.HexView(data)
				data.tofile(file)
		except Exception as e:
			logging.warning(e.args[0])  
			if "INVALID_LOG_PAGE" in e.args[0]: #INVALID_LOG_PAGE: The log page indicated is invalid.
				logging.info('Get Invailed LogPage (LID={})'.format(lid))
				data = None
			elif "INVALID_FIELD" in e.args[0]: # INVALID_FIELD: A reserved coded value or an unsupported value in a defined field
				logging.info('Get Invailed Field (LID={})'.format(lid))
				data = None
			else:
				pytest.fail("Get LogPage (LID={}) FAILED".format(lid))		
		return data		
	
	@pytest.fixture(scope = "class")
	def log_path(self):
		'''
		create path for logs
		'''
		hostname = self.find_host()
		log_path = os.path.join(os.path.dirname(__file__), hostname + "_over_mps_data_transfer_logs")
	
		if os.path.exists(log_path):
			shutil.rmtree(log_path)
		os.mkdir(log_path) 
		yield log_path
	
		logging.info(log_path)
		os.system('mv *.log ' + log_path)
		os.system('mv read_*.bin ' + log_path)
	
	@pytest.mark.timeout(timeout = 60, method = "signal") 
	def test_over_mps_data_transfer(self,nvme0,log_path):
		logging.info('Start test of Over MPS Admin command test')
		ctrl,ns = nvme0
		MPSMIN = 4096
		MDTS = ctrl.identify().mdts
		logpage_fixed_data_file = 'get_log_page_fixed_data.bin'
		security_recv_fixed_data_file = 'security_receive_fixed_data.bin'

		# max_data_per_cmd = ((2**MDTS)*(MPSMIN))
		# Dword align [4B, 4B < data size < 4KB, 4KB, 4KB < data size < 8KB, 8KB, 8KB < data size < 12KB, 12KB, 12KB < data size < 16KB, 16KB]
		# get logpage support <= 16KB data transfer 
		logpage_fixed_data = np.fromfile(logpage_fixed_data_file, dtype=np.uint8)
		for data_size in (4,4*random.randint(2,1024),4*1024,4*random.randint(1025,2048),4*2048,4*random.randint(2049,1024*3),4*3072,4*random.randint(1024*3+1,1024*4),4*4096):
			logging.info('Transfer data size = {} B'.format(data_size))
			read_file='read_dwalign_{}.bin'.format(data_size)
			data = self.logpage(ctrl,read_file, lid=1, size=data_size)
			ret = np.array_equal(np.frombuffer(data, dtype=np.uint8), logpage_fixed_data[0:data_size])
			if not ret:
				logging.error('check Dword align data transfer: {} FAILED'.format(data))
				pytest.fail('check Dword align data transfer FAILED')
			logging.info('data transfer PASSED')
		
		# Dword unalign [< 4B, 4B < data size < 4KB, 4KB, 4KB < data size < 8KB, 8KB, 8KB < data size < 12KB, 12KB, 12KB < data size < 16KB, 16KB, 16KB < data size < 64KB]
		# get logpage support <= 16KB data transfer 
		security_recv_fixed_data = np.fromfile(security_recv_fixed_data_file, dtype=np.uint8)
		for data_size in (random.randint(1,4),4*random.randint(2,1024)+1,4*random.randint(1025,2048)+1,4*2048,4*random.randint(2049,16*1024)+1,4*3072,4*random.randint(1024*3+1,1024*4)+1,4*4096,4*random.randint(1024*4+1,1024*16)+1,1024*64):
			logging.info('Transfer data size = {} B'.format(data_size))
			read_file='read_bytealign_{}.bin'.format(data_size)
			data = self.security_recv(ctrl,read_file,al=data_size)
			ret = np.array_equal(np.frombuffer(data[0:data_size], dtype=np.uint8), security_recv_fixed_data[0:data_size])
			if not ret:
				logging.error('check byte align data tranfer{} FAILED'.format(data[0:data_size]))
				pytest.fail('check byte align data transfer FAILED')
			else:
				if len(data) - data_size != 0:
					check_read_data = list(set(data[data_size:]))
					if len(check_read_data) != 1 or check_read_data[0] != 0:	# 4k size data will be returned, the data over read data size will be filled with 0
						logging.error('the data over read size is not be filled with 0: {}'.format(check_read_data))
						pytest.fail('the data over read size is not be filled with 0: FAILED')
				logging.info('data transfer PASSED')

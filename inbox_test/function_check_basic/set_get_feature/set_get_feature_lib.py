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
import logging
from sfvs.common import hexview
from sfvs.nvme import nvme
import time
import os
import subprocess

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')
class Set_Get_Feature:
	
	def __init__(self):
		host = nvme.Host.enumerate()[0]
		self.ctrl = host.controller.enumerate()[0]	
		self.namespace = self.ctrl.enumerate_namespace()[0]
		#self.logger = logger

	
	def get_feature(self, feature_id):
		'''
		get value of specified feature
		:return: value of feature, -1 if get failed
		'''
		with self.namespace as ns:
			try:				
				if feature_id == nvme.FeatureId.Arbitration:
					logging.info("get Arbitration value")
					data = ns.get_arbitration()
					logging.info("Arbitration Current: 0x{:08x}".format(data))
				
				if feature_id == nvme.FeatureId.PowerMgmt:
					logging.info("get Power Management value")
					data = ns.get_power_mgmt()
					logging.info("Power Management Current: 0x{:08x}".format(data))				
				
				if feature_id == nvme.FeatureId.LbaRange:
					logging.info("get LBA Range")
					data = ns.get_lba_range()
					logging.info("LBA Range Type Current: \n{}".format(hexview.HexView(data)))	
					
				if feature_id == nvme.FeatureId.TempThresh:
					logging.info("get Temperature ThreshHold value")
					data = ns.get_temperature_threshold()
					logging.info("Temperature ThreshHold value: 0x{:08x}".format(data))				

				if feature_id == nvme.FeatureId.ErrRecovery:
					logging.info("get current error recovery value")
					data = ns.get_error_recovery()
					logging.info("Error recovery Current: 0x{:08x}".format(data))	
					
				if feature_id == nvme.FeatureId.VolatileWriteCache:
					logging.info("get current volatile write cache value")
					data = ns.get_volatile_wc()
					logging.info("Volatile Write Cache Current: 0x{:08x}".format(data))
					
				if feature_id == nvme.FeatureId.NumofQueues:
					logging.info("get current number of queues value")
					data = ns.get_num_of_queues()
					logging.info("Number of Queues Current: 0x{:08x}".format(data))				
				
				if feature_id == nvme.FeatureId.IrqCoalesce:
					logging.info("get current Interrupt Coalescing value")
					data = ns.get_irq_coalesce()
					logging.info("Interrupt Coalescing Current: 0x{:08x}".format(data))	
					
				if feature_id == nvme.FeatureId.IrqConfig:
					logging.info("get current Interrupt Vector Configuration value")
					data = ns.get_irq_config()
					logging.info("Interrupt Vector Configuration Current: 0x{:08x}".format(data))
					
				if feature_id == nvme.FeatureId.WriteAtomicity:
					logging.info("get current Write Atomicity value")
					data = ns.get_write_atomicity()
					logging.info("Write Atomicity Current: 0x{:08x}".format(data))	
				
				if feature_id == nvme.FeatureId.AsyncEvent:
					logging.info("get current Asynchronous Event Configuration value")
					data = ns.get_async_event_cfg()
					logging.info("Asynchronous Event Configuration Current: 0x{:08x}".format(data))	
					
				if feature_id == nvme.FeatureId.PowerStateTrans:
					logging.info("get current Autonomous Power State Transition value")
					data = ns.get_auto_pst()
					logging.info("Autonomous Power State Transition Current: \n{}".format(hexview.HexView(data)))
					
				if feature_id == nvme.FeatureId.HostMemBuf:
					logging.info("get current Host Memory Buffer value")
					data = ns.get_host_mem_buf()
					logging.info("Host Memory Buffer Current: \n{}".format(hexview.HexView(data)))	
					
				if feature_id == nvme.FeatureId.TimeStamp:
					logging.info("get current TimeStamp value")
					data = ns.get_time_stamp()
					logging.info("TimeStamp Current: \n{}".format(hexview.HexView(data)))					
				
				if feature_id == nvme.FeatureId.KeepAliveTimer:
					logging.info("get current Keep Alive Timer value")
					data = ns.get_keep_alive_timer()
					logging.info("Keep Alive Timer Current: 0x{:08x}".format(data))	
					
				if feature_id == nvme.FeatureId.HCThermMgmt:
					logging.info("get current Host Controlled Thermal Management value")
					data = ns.get_hc_thermal_mgmt()
					logging.info("Host Controlled Thermal Management Current: 0x{:08x}".format(data))
					
				if feature_id == nvme.FeatureId.NoPowerStateConfig:
					logging.info("get current Non-Operational Power State Config value")
					data = ns.get_nonop_power_state()
					logging.info("Non-Operational Power State Config Current: 0x{:08x}".format(data))				
				
			except nvme.NVMeException as e:
				logging.warning(e, exc_info=False)
				return -1
			
		return data
	
	def set_feature(self, feature_id):
		'''
		set value of specified feature and check if set successfully
		:return: 0 is set passed, -1 if set failed
		'''		
		try:
			with self.ctrl as c:
				before_feature_value = self.get_feature(feature_id)
				if before_feature_value == -1:
					logging.error("Get value of {} failed".format(feature_id))
					return -1
				else:
					value_to_set = before_feature_value + 1
					logging.info("set new value to: 0x{:08x}".format(value_to_set))
					c.set_feature(
					nsid = 0,
				    feature_id = feature_id,
				    value = value_to_set,
				    cdw12 = 0,
					)
					#self.logger.info("get new value after set feature")
					new_feature_value = self.get_feature(feature_id)
					if new_feature_value == -1:
						logging.error("Get value of {} failed".format(feature_id))
						return -1
					else:
						#self.logger.info("New value after set feature: 0x{:08x}".format(new_feature_value))
						if value_to_set == new_feature_value:
							logging.info("Set feature passed: value is set")
							logging.info("Recover value to: 0x{:08x}".format(before_feature_value))
							c.set_feature(
						    nsid = 0,
						feature_id = feature_id,
						value = before_feature_value,
						cdw12 = 0,
					    )
						else:
							logging.error("test fail: value is not set")
							return -1
		except nvme.NVMeException as e:
			logging.error('Error: {}'.format(str(e)))	
			return -1
		return 0

	def set_feature_verify(self, feature_id, value_to_set, recover=True):
		'''
		set value of specified feature and check if set successfully
		:return: 0 is set passed, -1 if set failed
		'''
		try:
			with self.ctrl as c:
				before_feature_value = self.get_feature(feature_id)
				if before_feature_value == -1:
					logging.error("Get value of {} failed".format(feature_id))
					return -1
				else:
					logging.info("set new value to: 0x{:08x}".format(value_to_set))
					c.set_feature(
						nsid=0,
						feature_id=feature_id,
						value=value_to_set,
						cdw12=0,
					)
					# logging.info("get new value after set feature")
					new_feature_value = self.get_feature(feature_id)
					if new_feature_value == -1:
						logging.error("Get value of {} failed".format(feature_id))
						return -1
					else:
						# logging.info("New value after set feature: 0x{:08x}".format(new_feature_value))
						if value_to_set == new_feature_value:
							logging.info("Set feature passed: value is set")
							if recover == True:
								logging.info("Recover value to: 0x{:08x}".format(before_feature_value))
								c.set_feature(
									nsid=0,
									feature_id=feature_id,
									value=before_feature_value,
									cdw12=0,
								)
						else:
							logging.error("test fail: value is not set")
							return -1
		except nvme.NVMeException as e:
			print('Error: {}'.format(str(e)))
			return -1
		return 0

	def get_feature_lba(self,feature_id):
		'''
        set value of specified feature and check if set successfully
        :return: 0 is set passed, -1 if set failed
        '''
		get_feature_cmd = "nvme get-feature /dev/nvme0n1 -f 3 --raw-binary > lba_range_old"
		p1 = subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
		get_lba_result=p1.stdout.read().decode()
		if "INVALID_FIELD(4002)" in get_lba_result:
			logging.info("not support LbaRange TYPE to get feature")
			return -2
		logging.info("set new LBA range")
		set_geature_cmd = "nvme set-feature /dev/nvme0 -n 1 -f 3 -v 0 -l 4096 -d lba_new.raw"
		p1 = subprocess.Popen(set_geature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
		set_lba = p1.stdout.read().decode()
		logging.info(set_lba)
		logging.info("get current LBA range")
		get_feature_cmd = "nvme get-feature /dev/nvme0n1 -f 3 --raw-binary > lba_range_new"
		p1 = subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
		time.sleep(5)
		cmd="diff lba_range_new lba_new.raw"
		print(cmd)
		flag = os.system(cmd)
		if flag == 0:
			logging.info("set LBA range successfully")
			result = 0
		else:
			logging.error("LBA range set fail")
			result = -1
		set_geature_cmd = "nvme set-feature /dev/nvme0 -n 1 -f 3 -v 0 -l 4096 -d lba_range_old"
		p1 = subprocess.Popen(set_geature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
		set_lba = p1.stdout.read().decode()
		logging.info(set_lba)
		return result

	def set_feature_hmb(self, feature_id):
		'''
		set value of specified feature and check if set successfully
		:return: 0 is set passed, -1 if set failed
		'''
		try:
			with self.ctrl as c:
				before_feature_value = self.get_feature(feature_id)
				if before_feature_value == -1:
					logging.error("Get value of {} failed".format(feature_id))
					return -1
				else:
					get_feature_cmd="nvme get-feature /dev/nvme0 -f 0xd"
					p1=subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
					dis_hmb=p1.stdout.read().decode()
					logging.info(dis_hmb)

					logging.info("disable hmb")
					c.set_feature(
					nsid = 0,
					feature_id = feature_id,
					value = 0,
					cdw12 = 0,
					)
					time.sleep(5)
					p1=subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
					dis_hmb=p1.stdout.read().decode()
					logging.info(dis_hmb)
					if "00000000" not in dis_hmb:
						pytest.fail("----------------failed to disalbe HMB----------------stopped disable hmb test")
						return -1
					"""
					c.set_feature(
					nsid = 0,
					feature_id = feature_id,
					value = 1,
					cdw12 = 0x8000, 
					cdw13 = 0x264A2000, 
					cdw14 = 0x4, 
					cdw15 = 0x20,
					)
					"""
					logging.info("enable hmb")
					cmd="sudo nvme admin-passthru /dev/nvme0 --opcode=0x09 --cdw10=0x0d --cdw11=0x01 --cdw12=0x8000 --cdw13=0x264A2000 --cdw14=0x4 --cdw15=0x20"
					os.system(cmd)
					time.sleep(5)
					p1=subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
					hmb=p1.stdout.read().decode()
					logging.info(hmb)
					if "Current value:0x000001" not in hmb:
						pytest.fail("----------------failed to disalbe HMB----------------stopped disable hmb test")
						return -1
		except nvme.NVMeException as e:
			logging.info('Error: {}'.format(str(e)))
			return -1

		return 0

	def set_feature_apst(self,feature_id):
		try:
			with self.ctrl as c:
				before_feature_value = self.get_feature(feature_id)
				if before_feature_value == -1:
					logging.error("Get value of {} failed".format(feature_id))
					return -1
				else:
					get_feature_cmd = "nvme admin-passthru /dev/nvme0 --opcode=0x0A --cdw10=0x0c --data-len=256 --read"
					get_apst_structure_cmd="nvme admin-passthru /dev/nvme0 --opcode=0x0A --cdw10=0x0c --data-len=256 --read > apst_structure"
					enable_apst_cmd="nvme admin-passthru /dev/nvme0 --opcode=0x09 --cdw10=0x0c --cdw11=0x01 --write --data-len=256 --input-file=apst_enable"
					p1 = subprocess.Popen(get_apst_structure_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
					apst_structure = p1.stdout.read().decode()
					logging.info(apst_structure)

					logging.info("disable apst")
					disable_apst_cmd="nvme set-feature /dev/nvme0 -f 0x0c -v 0"
					p1 = subprocess.Popen(disable_apst_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
										  shell=True)
					disable_apst = p1.stdout.read().decode()
					logging.info(disable_apst)
					if "00000000" not in disable_apst:
						pytest.fail("----------------failed to disalbe apst----------------stopped disable apst test")
						return -1
					p1 = subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
										  shell=True)
					verify_status = p1.stdout.read().decode()
					logging.info(verify_status)
					if "00000000" not in verify_status:
						pytest.fail("----------------failed to disalbe apst----------------stopped disable apst test")
						return -1

					logging.info("enable apst")
					#self.logger.info("get new value after set feature")
					p1 = subprocess.Popen(enable_apst_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
										  shell=True)
					enable_aspt = p1.stdout.read().decode()
					logging.info(enable_aspt)
					p1 = subprocess.Popen(get_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
										  shell=True)
					verify_status = p1.stdout.read().decode()
					logging.info(verify_status)

					if "00000001" not in verify_status:
						pytest.fail("----------------failed to enable apst----------------stopped enable apst test")
						return -1
		except nvme.NVMeException as e:
			logging.error('Error: {}'.format(str(e)))
			return -1
		return 0

	def set_feature_NumofQueues(self,feature_id):
		try:
			with self.ctrl as c:
				before_feature_value = self.get_feature(feature_id)
				if before_feature_value == -1:
					logging.error("Get value of {} failed".format(feature_id))
					return -1
				else:
					logging.info("set new value:0x0f000e")
					set_feature_cmd="sudo nvme set-feature -f 0x07 /dev/nvme0n1 -v 0x0f000e"
					p1 = subprocess.Popen(set_feature_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
							  shell=True)
					set_NumofQueues = p1.stdout.read().decode()
					logging.info(set_NumofQueues)
					#if "CMD_SEQ_ERROR" not in set_NumofQueues:
					#	pytest.fail("the Set Features command should fail with status code of Command Sequence Error.")
					#	return -1
		except nvme.NVMeException as e:
			logging.error('Error: {}'.format(str(e)))
			return -1
		return 0
#if __name__ == "__main__":
#	
#	test = Set_Get_Feature()
	
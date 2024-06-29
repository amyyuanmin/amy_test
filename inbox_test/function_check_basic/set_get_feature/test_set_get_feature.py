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
import os
import shutil
from sfvs.nvme import nvme
from set_get_feature.set_get_feature_lib import Set_Get_Feature

logging.basicConfig(level=logging.WARNING,format='%(asctime)s - %(levelname)s : %(message)s')

class Test_Set_Get_Feature:
	
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
	
	#@pytest.fixture(scope = 'class')
	#def log_setup(self, log_path):
	#	'''
	#	setup log for both output and log file
	#	'''
	#	logger = logging.getLogger()
	#	logger.setLevel(logging.INFO)
	#	output_handler = logging.StreamHandler()
	#	FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
	#	run_log = "set_get_feature_log.log"
	#	handler = logging.FileHandler(run_log)
	#	output_handler.setFormatter(FORMATTER)
	#	handler.setFormatter(FORMATTER)
	#	logger.addHandler(handler)    
	#	logger.addHandler(output_handler)
	#	test = Set_Get_Feature(logger)
	#	yield logger, test
	#	os.system('mv *.log ' + log_path)
		
	
	@pytest.fixture(scope = "class")
	def log_path(self):
		'''
		create path for logs
		'''
		hostname = self.find_host()
		log_path = os.path.join(os.path.dirname(__file__), hostname + "_set_get_feature_logs")
	
		if os.path.exists(log_path):
			shutil.rmtree(log_path)
		os.mkdir(log_path) 
	
		print(log_path)
		os.system('mv *.log ' + log_path)
		
	#@pytest.fixture(scope="class")
	#def summary_log(self, log_path):
		#'''
		#summary result log for each case
		#'''
		#summary_log = log_path + '/set_get_feature_result.log'        
		#yield summary_log   	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 
	def arbitration(self,log_path):
		test = Set_Get_Feature()
		logging.info('Start test of arbitration')
		result = test.set_feature(nvme.FeatureId.Arbitration)
		if result != -1:
			logging.info('Test set arbitration passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Arbitration', 'Pass'))
		else:
			logging.info('Test set arbitration failed!')
			pytest.fail('Test set arbitration failed!')

	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 
	def power_mgmt(self):
		test = Set_Get_Feature()
		logging.info('Start test of Power Management')
		for i in range(0,5):
			result = test.set_feature_verify(nvme.FeatureId.PowerMgmt,i) 
			# result = test.get_feature(nvme.FeatureId.PowerMgmt)
			if result != -1:
				logging.info('Test set Power Management passed!')
				# with open(summary_log, 'a+') as f:
				# 	f.write('%-35s:%-45s\n'%('Power Mgmt', 'Pass'))
			else:
				logging.info('Test set Power Management failed!')
				pytest.fail('Test set Power Management failed!')	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout=60,method="signal") 
	def lba_range(self):
		test = Set_Get_Feature()
		logging.info('Start test of LBA range')
		# result = test.set_feature(nvme.FeatureId.LbaRange)
		result = test.get_feature_lba(nvme.FeatureId.LbaRange)
		if result == 0:
			logging.info('Test set LBA range passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('LBA Range', 'Pass'))
		elif result == -2:
			logging.info('LBA range is not supported!')
			pytest.skip('Test set LBA range skipped!')
		else:
			logging.info('Test set LBA range failed!')
			pytest.fail('Test set LBA range failed!')	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 
	def temperature_threshhold(self):
		test = Set_Get_Feature()
		logging.info('Start test of temperature threshhold')
		result = test.set_feature(nvme.FeatureId.TempThresh)
		if result != -1:
			logging.info('Test set temperature threshhold passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Temperature Threshhold', 'Pass'))
		else:
			logging.info('Test set temperature threshhold failed!')
			pytest.fail('Test set temperature threshhold failed!')	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 	
	def err_recovery(self):
		test = Set_Get_Feature()
		logging.info('Start test of error recovery')
		result = test.set_feature(nvme.FeatureId.ErrRecovery)  
		# result = test.get_feature(nvme.FeatureId.ErrRecovery)
		if result != -1:
			logging.info('Test set Error Recovery passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Error Recovery', 'Pass'))
		else:
			logging.info('Test set Error Recovery failed!')
			pytest.fail('Test set Error Recovery failed!')		
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 		
	def volatile_wc(self):
		test = Set_Get_Feature()
		logging.info('Start test of Volatile Write Cache')
		result = test.set_feature(nvme.FeatureId.VolatileWriteCache)
		if result != -1:
			logging.info('Test set Volatile Write Cache passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Volatile Write Cache', 'Pass'))
		else:
			logging.info('Test set Volatile Write Cache failed!')
			pytest.fail('Test set Volatile Write Cache failed!')		
	
	@pytest.mark.timeout(timeout = 60, method = "signal") 		
	def test_number_of_queues(self):
		test = Set_Get_Feature()
		logging.info('Start test of Number Of Queues')
		result = test.set_feature_NumofQueues(nvme.FeatureId.NumofQueues)
		if result != -1:
			logging.info('Test set Number Of Queues passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Number Of Queues', 'Pass'))
		else:
			logging.info('Test set Number Of Queues failed!')
			pytest.fail('Test set Number Of Queues failed!')	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 		
	def interrupt_coalescing(self):
		test = Set_Get_Feature()
		logging.info('Start test of Interrupt Coalescing')
		result = test.set_feature(nvme.FeatureId.IrqCoalesce)
		if result != -1:
			logging.info('Test set Interrupt Coalescing passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Interrupt Coalescing', 'Pass'))
		else:
			logging.info('Test set Interrupt Coalescing failed!')
			pytest.fail('Test set Interrupt Coalescing failed!')	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 		
	def interrupt_vector_config(self):
		test = Set_Get_Feature()
		logging.info('Start test of Interrupt Vector Configuration')
		result = test.set_feature(nvme.FeatureId.IrqConfig)
		if result != -1:
			logging.info('Test set Interrupt Vector Configuration passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Interrupt Vector Configuration', 'Pass'))
		else:
			logging.info('Test set Interrupt Vector Configuration failed!')
			pytest.fail('Test set Interrupt Vector Configuration failed!')	
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 		
	def write_atomicity(self):
		test = Set_Get_Feature()
		logging.info('Start test of Write Atomicity')
		result = test.set_feature(nvme.FeatureId.WriteAtomicity)
		if result != -1:
			logging.info('Test set Write Atomicity passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Write Atomicity', 'Pass'))
		else:
			logging.info('Test set Write Atomicity failed!')
			pytest.fail('Test set Write Atomicity failed!')		
	
	@pytest.mark.skip
	@pytest.mark.timeout(timeout = 60, method = "signal") 		
	def async_event(self):
		test = Set_Get_Feature()
		logging.info('Start test of Asynchronous Event Configuration')
		result = test.set_feature(nvme.FeatureId.AsyncEvent)
		if result != -1:
			logging.info('Test set Asynchronous Event Configuration passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Asynchronous Event Configuration', 'Pass'))
		else:
			logging.info('Test set Asynchronous Event Configuration failed!')
			pytest.fail('Test set Asynchronous Event Configuration failed!')

	@pytest.mark.skip
	@pytest.mark.timeout(timeout=60,method="signal") 
	def power_state_transition(self):
		test = Set_Get_Feature()
		logging.info('Start test of Autonomous Power State Transition')
		result = test.set_feature_apst(nvme.FeatureId.PowerStateTrans)
		if result != -1:
			logging.info('Test set Autonomous Power State Transition passed!')
			#with open(summary_log, 'a+') as f:
				#f.write('%-35s:%-45s\n'%('Autonomous Power State Transition', 'Pass'))			
		else:
			logging.info('Test set Autonomous Power State Transition failed!')
			#pytest.fail('Test set Autonomous Power State Transition failed!')

	@pytest.mark.skip
	@pytest.mark.timeout(timeout=60,method="signal") 		
	def host_mem_buffer(self):
		test = Set_Get_Feature()
		logging.info('Start test of Host Memory Buffer')
		result = test.set_feature_hmb(nvme.FeatureId.HostMemBuf)
		if result != -1:
			logging.info('Test set Host Memory Buffer passed!')
			# with open(summary_log, 'a+') as f:
			# 	f.write('%-35s:%-45s\n'%('Host Memory Buffer', 'Pass'))
		else:
			logging.info('Test set Host Memory Buffer failed!')
			pytest.fail('Test set Host Memory Buffer failed!')	
	#@pytest.mark.timeout(timeout=60,method="signal") 		
	#def test_time_stamp(self, summary_log):
		#logger.info('Start test of TimeStamp')
		#result = test.set_feature(nvme.FeatureId.TimeStamp)
		#if result != -1:
			#logger.info('Test set TimeStamp passed!')
			#with open(summary_log, 'a+') as f:
				#f.write('%-35s:%-45s\n'%('TimeStamp', 'Pass'))			
		#else:
			#logger.info('Test set TimeStamp failed!')
			#pytest.fail('Test set TimeStamp failed!')	
	
	#@pytest.mark.timeout(timeout=60,method="signal") 		
	#def test_keep_alive_timer(self, summary_log):
		#logger.info('Start test of Keep Alive Timer')
		#result = test.set_feature(nvme.FeatureId.KeepAliveTimer)
		#if result != -1:
			#logger.info('Test set Keep Alive Timer passed!')
			#with open(summary_log, 'a+') as f:
				#f.write('%-35s:%-45s\n'%('Keep Alive Timer', 'Pass'))			
		#else:
			#logger.info('Test set Keep Alive Timer failed!')
			#pytest.fail('Test set Keep Alive Timer failed!')	
	
	#@pytest.mark.timeout(timeout=60,method="signal") 		
	#def test_hc_thermal_mgmt(self, summary_log):
		#logger.info('Start test of Host Controlled Thermal Management')
		#result = test.set_feature(nvme.FeatureId.HCThermMgmt)
		#if result != -1:
			#logger.info('Test set Host Controlled Thermal Management passed!')
			#with open(summary_log, 'a+') as f:
				#f.write('%-35s:%-45s\n'%('Host Controlled Thermal Management', 'Pass'))			
		#else:
			#logger.info('Test set Host Controlled Thermal Management failed!')
			#pytest.fail('Test set Host Controlled Thermal Management failed!')	
	
	#@pytest.mark.timeout(timeout=60,method="signal") 		
	#def test_nonop_power_state(self, summary_log):
		#logger.info('Start test of Non-Operational Power State Config')
		#result = test.set_feature(nvme.FeatureId.NoPowerStateConfig)
		#if result != -1:
			#logger.info('Test set Non-Operational Power State Config passed!')
			#with open(summary_log, 'a+') as f:
				#f.write('%-35s:%-45s\n'%('Non-Operational Power State Config', 'Pass'))			
		#else:
			#logger.info('Test set Non-Operational Power State Config failed!')
			#pytest.fail('Test set Non-Operational Power State Config failed!')
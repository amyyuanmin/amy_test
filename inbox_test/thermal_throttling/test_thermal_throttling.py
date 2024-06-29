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
import os
import random
from thermal_throttling_lib import Thermal_Throttling
from sfvs.nvme import nvme
import time

class Test_Thermal_Throttling:
	
	@pytest.fixture(scope='class')
	def test_setup(self):
		'''
		setup log for both output and log file
		'''
		lib = Thermal_Throttling('thermal_throttling_log.log')
		logger = lib.logger
		log_path = lib.log_prepare('thermal_throttling_logs')
		tt_result = log_path + "/thermal_throttling_result.log"
		yield lib, logger
		os.system('mv *.log '+log_path)
		os.system('mv ' + lib.runtime_perf_log + ' ' + log_path)
	
	def test_identify_HCTM(self, test_setup):
		'''
		Check the Bit 0 of the HCTMA field to determine of the DUT supports thermal throttling, if bit 0 is set to 0 this test is not applicable
		Get the value of MNTMT and MXTMT if supported
		'''
		lib, logger = test_setup
		
		logger.info('++++++Start test of identify of HCTM++++++')
		
		#hctma, mntmt, mxtmt = lib.identify_HCTM()
		if lib.hctma == 0x1 and lib.mntmt != 0 and lib.mxtmt != 0 and lib.mntmt < lib.mxtmt:
			#lib.save_summary(summary_log, 'Pass', 'Identify HCTM')
			pass

		else:
			#lib.save_summary(summary_log, 'Fail', 'Identify HCTM')
			logger.error('Identify fail')
			pytest.fail('Identify fail')
	
	def test_get_feature_HCTM(self, test_setup):
		'''
		Get the default value of HCTM
		the higher 16 bit is TMT1 and lower 16 bit is TMT2 and both in the range of [MNTMT, MXTMT]
		'''
		lib, logger = test_setup
				
		logger.info('++++++Start test of get value of HCTM++++++')
		
		#hctma, mntmt, mxtmt = lib.identify_HCTM()
		#tmt1, tmt2 = lib.get_current_tmt()
		temp_dict, kelvin = lib.get_smart_temperature()
		if lib.mntmt <= lib.tmt1 < lib.tmt2 <= lib.mxtmt and kelvin < lib.tmt1:
			#lib.save_summary(summary_log, 'Pass', 'Get HCTM value')
			pass
		else:
			#lib.save_summary(summary_log, 'Fail', 'Get HCTM value')
			lib.flag = -1
			logger.error('Get HCTM value fail')
			pytest.fail('Get HCTM value fail')	
	
	def test_set_feature_tmt(self, test_setup):
		'''
		TMT1/TMT2 in CDW11, MNTMT(predefined 10 degree centigrade, i.e. 283K) <= TMT1 < TMT2 <= MXTMT(predefined 120 degree centigrade, i.e. 393K)
		'''
		lib, logger = test_setup
		logger.info('++++++Start test of set feature TMT1/TMT2++++++')
		
		for i in range(1, 20):
			#MNTMT < TMT1 < TMT2 < MXTMT
			tmt1 = random.randint(lib.mntmt + 1, lib.mxtmt - 2)
			tmt2 = random.randint(tmt1 + 1, lib.mxtmt - 1)
			new_value = (tmt1 << 16) + tmt2
			logger.info('Set TMT1/TMT2 to value {}/{} to let MNTMT < TMT1 < TMT2 < MXTMT'.format(lib.kelvin_centigrade_map(tmt1), lib.kelvin_centigrade_map(tmt2)))
			
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			if result == -1:
				break
			
			#MNTMT = TMT1 < TMT2 < MXTMT
			tmt1 = lib.mntmt
			tmt2 = random.randint(tmt1 + 1, lib.mxtmt - 1)
			new_value = (tmt1 << 16) + tmt2
			logger.info('Set TMT1/TMT2 to value {}/{} to let MNTMT = TMT1 < TMT2 < MXTMT'.format(lib.kelvin_centigrade_map(tmt1), lib.kelvin_centigrade_map(tmt2)))
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			if result == -1:
				break			
			
			#MNTMT < TMT1 < TMT2 = MXTMT
			tmt2 = lib.mxtmt
			tmt1 = random.randint(lib.mntmt + 1, tmt2 - 1)
			new_value = (tmt1 << 16) + tmt2
			logger.info('Set TMT1/TMT2 to value {}/{} to let MNTMT < TMT1 < TMT2 = MXTMT'.format(lib.kelvin_centigrade_map(tmt1), lib.kelvin_centigrade_map(tmt2)))
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			if result == -1:
				break				
			
			#MNTMT = TMT1 < TMT2 = MXTMT
			tmt2 = lib.mxtmt
			tmt1 = lib.mntmt
			new_value = (tmt1 << 16) + tmt2
			logger.info('Set TMT1/TMT2 to value {}/{} to let MNTMT = TMT1 < TMT2 = MXTMT'.format(lib.kelvin_centigrade_map(tmt1), lib.kelvin_centigrade_map(tmt2)))
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			
			#cancel throttling
			result = lib.cancel_throttling()
			
			if result == -1:
				break				
			
		if result == -1:
			#lib.save_summary(summary_log, 'Fail', 'Set feature valid TMT')
			logger.error('Set value of TMT failed')
			pytest.fail('Set value of TMT failed')
		#else:
			#lib.save_summary(summary_log, 'Pass', 'Set feature valid TMT')
		
	def test_set_feature_tmt_invalid(self, test_setup):
		'''
		TMT1/TMT2: value less or greater than MNTMT/MXTMT - Invalid Field in Command.
		TMT1 >= TMT2 / set TMT2 <= TMT1: Invalid Field in Command.
		'''
		lib, logger = test_setup
		logger.info('++++++Start test of set feature TMT1/TMT2 with invalid values, errors are expected++++++')
			
		for i in range(1, 20):
			tmt_low = random.randint(273, lib.mntmt - 1) #should be a temperature larger than 0c
			tmt_high = random.randint(lib.mxtmt + 1, lib.mxtmt * 2)
			tmt1 = random.randint(lib.mntmt, lib.mxtmt - 1)
			tmt2 = random.randint(tmt1 + 1, lib.mxtmt)
			
			new_value = (tmt_low << 16) + tmt2		
			logger.info('Set TMT1 to value {} which is lower than MNTMT, TMT2 to value {}'.format(lib.kelvin_centigrade_map(tmt_low), lib.kelvin_centigrade_map(tmt2)))
			
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			if result != -1:
				break
			
			new_value = (tmt1 << 16) + tmt_high
			logger.info('Set TMT2 to value {} which is larger than MXTMT, TMT1 to value {}'.format(lib.kelvin_centigrade_map(tmt_high), lib.kelvin_centigrade_map(tmt1)))
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			if result != -1:
				break
			
			new_value = (tmt2 << 16) + tmt1
			logger.info('Set TMT1/TMT2 to value {}/{} let TMT1 > TMT2'.format(lib.kelvin_centigrade_map(tmt2), lib.kelvin_centigrade_map(tmt1)))
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)
			if result != -1:
				break			
			
			new_value = (tmt1 << 16) + tmt1
			logger.info('Set TMT1/TMT2 to value {}/{} let TMT1 = TMT2'.format(lib.kelvin_centigrade_map(tmt2), lib.kelvin_centigrade_map(tmt1)))
			result = lib.set_feature(nvme.FeatureId.HCThermMgmt, new_value)	
			if result != -1:
				break			
		
		if result != -1:
			#lib.save_summary(summary_log, 'Fail', 'Set feature invalid TMT')
			logger.error('Set value of TMT successfully, but test failed')
			pytest.fail('Set value of TMT successfully, but test failed')
		#else:
			#lib.save_summary(summary_log, 'Pass', 'Set feature invalid TMT')	
			
		
	def test_light_throttling(self, test_setup):
		
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of light throttling++++++')	
		time.sleep(40) #wait 10 more seconds to let the last 30 lines are all performance data
		iops_before = lib.get_IOPS_30s()
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')			
		ret = lib.trigger_light_throttling()
		if ret == 1:
			pytest.skip('Ignore test')
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling test failed')			
		
		
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
		
		iops_after = lib.get_IOPS_30s()
		if iops_after == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		
		if ( -10 > (iops_after - iops_before) > 0):  #reasonable gap, should be adjusted later
			lib.flag = -1
			logger.error('Light throttling does not work, test failed')
			pytest.fail('Light throttling does not work, test failed')
	
		if (lib.cancel_throttling() == -1):
			lib.flag = -1
			logger.error('Cancel throttling failed, Light throttling test failed')
			pytest.fail('Light throttling test failed')			
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
	
	def test_light_throttling_tmt1_equal(self, test_setup):
		
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')			
		logger.info('++++++Start test of light throttling, TMT1 = T++++++')	
		time.sleep(30)
		iops_before = lib.get_IOPS_30s()
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		ret = lib.trigger_light_throttling_tmt1_equal()
		if ret == 1:
			pytest.skip('Ignore test')
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling test failed')			
		
		
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
		
		iops_after = lib.get_IOPS_30s()
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		if (iops_after >= iops_before):
			lib.flag = -1
			logger.error('Light throttling does not work, test failed')
			pytest.fail('Light throttling does not work, test failed')
	
		if (lib.cancel_throttling() == -1):
			lib.flag = -1
			logger.error('Cancel throttling failed, light throttling test failed')
			pytest.fail('Light throttling test failed')			
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
				
		
	def test_heavy_throttling(self, test_setup):
		
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of heavy throttling++++++')	
		time.sleep(30)
		iops_before = lib.get_IOPS_30s()
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		ret = lib.trigger_heavy_throttling()	
		if ret == 1:
			pytest.skip('Ignore test')
		if ( ret == -1):
			lib.flag = -1
			logger.error('Heavy throttling failed')
			pytest.fail('Heavy throttling test failed')			
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
		iops_after = lib.get_IOPS_30s()	
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		if ((iops_before - iops_after)/iops_after < 0): #just temperary drop value, need adjust later
			lib.flag = -1
			logger.error('Light throttling does not work, test failed')
			pytest.fail('Light throttling does not work, test failed')		
		
		lib.cancel_throttling()
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
	
	def test_heavy_throttling_tmt2_equal(self, test_setup):
		
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of heavy throttling: TMT2 = T++++++')	
		time.sleep(30)
		iops_before = lib.get_IOPS_30s()
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		ret = lib.trigger_heavy_throttling_tmt2_equal()	
		if ret == 1:
			pytest.skip('Ignore test')
		if ( ret == -1):
			lib.flag = -1
			logger.error('Heavy throttling failed')	
			pytest.fail('Heavy throttling test failed')			
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
		iops_after = lib.get_IOPS_30s()	
		if iops_before == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		if ((iops_before - iops_after)/iops_after < 0): #just temperary drop value, need adjust later
			lib.flag = -1
			logger.error('Light throttling does not work, test failed')
			pytest.fail('Light throttling does not work, test failed')		
		
		lib.cancel_throttling()
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
	
	def test_light_heavy_throttling(self, test_setup):
				
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of light - heavy throttling++++++')	
		time.sleep(30)
		iops_1 = lib.get_IOPS_30s()
		if iops_1 == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		ret = lib.trigger_light_throttling()
		if ret == 1:
			pytest.skip('Ignore test')	
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling test failed')			
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
		
		iops_2 = lib.get_IOPS_30s()
		if iops_2 == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		ret = lib.trigger_heavy_throttling()
		if ( ret == -1):
			lib.flag = -1
			logger.error('Heavy throttling failed')
			pytest.fail('Heavy throttling failed')			
		
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
		
		if (iops_2 >= iops_1):
			lib.flag = -1
			logger.error('Light throttling does not work, test failed')
			pytest.fail('Light throttling does not work, test failed')		
		iops_3 = lib.get_IOPS_30s()
		if iops_3 == 0:
			lib.flag = -1
			logger.error('There might be Marvo IO error occur, please check')
			pytest.fail('There might be Marvo IO error occur, please check')		
		
		if ((iops_1 - iops_3)/iops_3 < 0): #just temperary drop value, need adjust later
			lib.flag = -1
			logger.error('Heavy throttling does not work, test failed')
			pytest.fail('Heavy throttling does not work, test failed')		
		
		lib.cancel_throttling()
		
		if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
	
	
	def test_light_throttling_repeat(self, test_setup):
		'''
		repeat: (light->cancel)loop
		'''						
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of light throttling - repeat for 1000 times++++++')	
		time.sleep(30)
		
		for count in range(1, 1000):
			logger.info('Test loop: {}'.format(count))
			ret = lib.trigger_light_throttling()	
			if ret == 1:
				logger.info('Skip this round')
				if count ==999:
					pytest.skip('Ignore the whole test')
				else:
					continue
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
			
			lib.cancel_throttling()
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')	
	
	
	def test_light_heavy_throttling_light_repeat(self, test_setup):
		'''
		repeat: (light->cancel)loop->light->heavy->light->cancel
		'''							
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of light - heavy throttling - light repeat for 1000 times++++++')	
		time.sleep(30)
		
		for count in range(1, 1000):
			logger.info('Test loop: {}'.format(count))
			ret = lib.trigger_light_throttling()	
			if ret == 1:
				logger.info('Skip this round')
				if count ==999:
					pytest.skip('Ignore the whole test')
				else:
					continue
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
			
			lib.cancel_throttling()
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')	
		
		ret = lib.trigger_light_throttling()	
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling failed')				
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
		
		ret = lib.trigger_heavy_throttling()	
		if ( ret == -1):
			lib.flag = -1
			logger.error('Heavy throttling failed')	
			pytest.fail('Heavy throttling failed')				
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')
	
		ret = lib.trigger_light_throttling()	
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling failed')	
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')	
		
		lib.cancel_throttling()
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
	
	def test_light_heavy_throttling_heavy_repeat(self, test_setup):
		'''
		repeat: light->(heavy->light)loop->cancel
		'''				
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of light - heavy throttling - heavy repeat for 1000 times++++++')	
		time.sleep(30)
		
		ret = lib.trigger_light_throttling()	
		if ret == 1:
			pytest.skip('Ignore this test')
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling failed')			
		
		for count in range(1, 1000):
			logger.info('Test loop: {}'.format(count))
			ret = lib.trigger_heavy_throttling()	
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
		
			ret = lib.trigger_light_throttling()	
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')	
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')			
			
		lib.cancel_throttling()
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')			
	
	def test_light_heavy_throttling_repeat(self, test_setup):
		'''
		repeat: light->heavy->light->cancel and loop
		'''
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')			
		logger.info('++++++Start test of light - heavy throttling - repeat for 1000 times++++++')	
		time.sleep(30)
		
		for count in range(1, 1000):
			logger.info('Test loop: {}'.format(count))
			ret = lib.trigger_light_throttling()
			if ret == 1:
				logger.info('Skip this round')
				if count ==999:
					pytest.skip('Ignore the whole test')
				else:
					continue
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
			
			ret = lib.trigger_heavy_throttling()
			if ( ret == -1):
				lib.flag = -1
				logger.error('Heavy throttling failed')
				pytest.fail('Heavy throttling failed')				
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')		
			
			ret = lib.trigger_light_throttling()
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')			
			
			lib.cancel_throttling()
			
			if (lib.check_thread_status(lib.t, 4) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')	
	
	def test_light_throttling_longtime(self, test_setup):
				
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')			
		logger.info('++++++Start test of light throttling for long time - for 3 hours++++++')	
		time.sleep(30)
		
		for count in range(1, 360):
			#check every 30 seconds, if IO fail, test fail, if throttling restored, trigger again, otherwise, keep running.
			ret = lib.trigger_light_throttling()	
			if ret == 1:
				logger.info('Skip this round')
				if count ==359:
					pytest.skip('Ignore the whole test')
				else:
					continue
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 10) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
			
		lib.cancel_throttling()
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')	
	
	
	def test_light_heavy_throttling_longtime(self, test_setup):
				
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')			
		logger.info('++++++Start test of light - heavy throttling for long time - heavy for 3 hours++++++')	
		time.sleep(30)
		
		ret = lib.trigger_light_throttling()
		if ret == 1:
			pytest.skip('Ignore test')
		if ( ret == -1):
			lib.flag = -1
			logger.error('Light throttling failed')
			pytest.fail('Light throttling failed')				
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
		
		for count in range(1, 360):
			#check every 30 seconds, if IO fail, test fail, if throttling restored, trigger again, otherwise, keep running.
			ret = lib.trigger_light_throttling()	
			if ret == 1:
				logger.info('Skip this round')
				if count ==999:
					pytest.skip('Ignore the whole test')
				else:
					continue
			if ( ret == -1):
				lib.flag = -1
				logger.error('Light throttling failed')
				pytest.fail('Light throttling failed')				
			
			if (lib.check_thread_status(lib.t, 10) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
			
		lib.cancel_throttling()
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')		
	
	
	def test_heavy_throttling_longtime(self, test_setup):
					
		lib, logger = test_setup
		if lib.flag == -1:
			logger.error('Test failed due to last failure')
			pytest.exit('Test failed due to last failure')		
		logger.info('++++++Start test of heavy throttling for long time - for 3 hours++++++')	
		time.sleep(30)
		
		for count in range(1, 360):
			#check every 30 seconds, if IO fail, test fail, if throttling restored, trigger again, otherwise, keep running.
			ret = lib.trigger_heavy_throttling()	
			if ret == 1:
				logger.info('Skip this round')
				if count ==999:
					pytest.skip('Ignore the whole test')
				else:
					continue
			if ( ret == -1):
				lib.flag = -1
				logger.error('Heavy throttling failed')
				pytest.fail('Heavy throttling failed')				
			
			if (lib.check_thread_status(lib.t, 10) == -1):
				lib.flag = -1
				logger.error('Marvo IO error occur, test failed')
				pytest.fail('Marvo IO error occur, test failed')
			
		lib.cancel_throttling()
		
		if (lib.check_thread_status(lib.t, 10) == -1):
			lib.flag = -1
			logger.error('Marvo IO error occur, test failed')
			pytest.fail('Marvo IO error occur, test failed')	
		
	# No need to cover reset scenario
	# def test_light_throttling_nvme_reset(self, test_setup):		
	# 	lib, logger = test_setup
	# 	if lib.flag == -1:
	# 		logger.error('Test failed due to last failure')
	# 		pytest.exit('Test failed due to last failure')		
	# 	logger.info('++++++Start test of light throttling and nvme reset++++++')
	# 	time.sleep(10)
	# 	os.system('sudo killall Marvo')  #Currently no io involved during reset
	# 	time.sleep(10)
	# 	ret = lib.trigger_light_throttling()
	# 	if ret == 1:
	# 			pytest.skip('Skip this test')
				
	# 	if ( ret == -1):
	# 		lib.flag = -1
	# 		logger.error('Light throttling test with NVMe reset failed')
	# 		pytest.fail('Light throttling test with NVMe reset failed')			
		
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#lib.flag = -1
	# 		#pytest.fail('Marvo IO error occur, test failed')
		
	# 	lib.nvme_reset()
	# 	time.sleep(5)
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#lib.flag = -1
	# 		#pytest.fail('Marvo IO error occur, test failed')
		
	# 	tmt1_after, tmt2_after = lib.get_current_tmt()
		
	# 	if tmt1_after == ret[1] and tmt2_after == ret[2]:  #should check IO for reference, currently manually check
	# 		logger.info('Thermal works after reset')
	# 	else:
	# 		lib.flag = -1
	# 		logger.error('Thermal does not work after reset')
	# 		pytest.fail('Thermal does not work after reset')
		
	# 	if (lib.cancel_throttling() == -1):
	# 		lib.flag = -1
	# 		logger.error('Light throttling with NVMe reset test failed')
	# 		pytest.fail('Light throttling with NVMe reset test failed')			
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#lib.flag = -1
	# 		#pytest.fail('Marvo IO error occur, test failed')	
	
	# def test_light_heavy_throttling_nvme_reset(self, test_setup):
	# 	'''
	# 	currently no IO for reset case
	# 	thought: maybe run IO before reset and get average IOPS, stop IO and reset and then start IO again, compare two IOPS
	# 	'''
	# 	lib, logger = test_setup
	# 	if lib.flag == -1:
	# 		logger.error('Test failed due to last failure')
	# 		pytest.exit('Test failed due to last failure')		
	# 	logger.info('++++++Start test of light-heavy throttling and nvme reset++++++')	
	# 	#time.sleep(30)
	# 	ret = lib.trigger_light_throttling()
	# 	if ret == 1:
	# 			pytest.skip('Skip this test')
		
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#pytest.fail('Marvo IO error occur, test failed')
		
	# 	ret, tmt1, tmt2 = lib.trigger_heavy_throttling()
		
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#pytest.fail('Marvo IO error occur, test failed')		
		
	# 	lib.nvme_reset()
	# 	time.sleep(5)
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#pytest.fail('Marvo IO error occur, test failed')
		
	# 	tmt1_after, tmt2_after = lib.get_current_tmt()
		
	# 	if tmt1_after == tmt1 and tmt2_after == tmt2:  #should check IO for reference, currently manually check
	# 		logger.info('Thermal works after reset')
	# 	else:
	# 		lib.flag = -1
	# 		logger.error('Thermal does not work after reset')
	# 		pytest.fail('Thermal does not work after reset')

	# 	if (lib.cancel_throttling() == -1):
	# 		lib.flag = -1
	# 		logger.error('Light-heavy throttling with NVMe reset test failed')
	# 		pytest.fail('Light-heavy throttling with NVMe reset test failed')	
	# 	#if (lib.check_thread_status(lib.t, 10) == -1): #check every 3 seconds for 10 times
	# 		#pytest.fail('Marvo IO error occur, test failed')	
		

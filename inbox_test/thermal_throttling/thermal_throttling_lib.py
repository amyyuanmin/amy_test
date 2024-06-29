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
from sfvs.common import hexview
from sfvs.nvme import nvme
import os
import shutil
import logging
import random
import subprocess
import threading
import time

class Thermal_Throttling:
	
	def __init__(self, run_log):
		host = nvme.Host.enumerate()[0]
		self.ctrl = host.controller.enumerate()[0]	
		self.namespace = self.ctrl.enumerate_namespace()[0]
		self.logger = logging.getLogger()
		self.logger.setLevel(logging.INFO)
		#output_handler = logging.StreamHandler()
		FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
		handler = logging.FileHandler(run_log)
		#output_handler.setFormatter(FORMATTER)
		handler.setFormatter(FORMATTER)
		self.logger.addHandler(handler)    
		#self.logger.addHandler(output_handler)	
		self.hctma, self.mntmt, self.mxtmt = self.identify_HCTM()
		
		marvo_tool_directory = '/home/fte/marvo'
		self.t=threading.Thread(target=self.run_marvo_perf, args=(marvo_tool_directory,)) #, is required, otherwise, each char is treat as one para
		
		self.t.setDaemon(True) #marvo not exit after test run
		os.system('sudo killall Marvo') #kill marvo before testing
		self.t.start()
		self.runtime_perf_log = os.path.join(marvo_tool_directory, "log", "Drive_1.log") #runtime marvo perf log, used to check runtime t-put
		
		self.tmt1, self.tmt2 = self.get_current_tmt()
		self.flag = 0
	
	def log_prepare(self, log_folder):
		'''
		prepare log related:
		log_path - full path of logs to be saved after all
		#summary log - result summary for each case
		'''	
		hostname = self.find_host()
		log_path = os.path.join(os.path.dirname(__file__), hostname+"_"+log_folder)
	
		if os.path.exists(log_path):
			shutil.rmtree(log_path)
		os.mkdir(log_path) 	
		
		#summary_log = log_path + '/' + summary_log        
		
		return log_path		
	
	def find_host(self):
		'''
		get host name of current test bed
		'''
		cmd="cat /etc/hostname"
		result=os.popen(cmd)
		host_name=result.read().strip().upper()
		self.logger.info("host_name at testbed is {}".format(host_name))
		result.close()
		return host_name
	
	#def save_summary(self, summary_log, result, item):
		#with open(summary_log, 'a+') as f:
			#self.logger.info('Test of {} {}!'.format(item, result))
			#f.write('%-35s:%-10s\n'%(item, result))	
	
	def identify_HCTM(self):
		'''
		get identify data to check if Host Control Thermal Mgmt supported and MNTMT/MXTMT values
		'''
		try:
			with self.ctrl:
				# Query Controller Identify data and print
				data = self.ctrl.identify()
				hctma = data.hctma
				mntmt = data.mntmt
				mxtmt = data.mxtmt
				self.logger.info("Value of HCTMA is: {}".format(hctma)) 
				self.logger.info("Value of MNTMT is: {}".format(mntmt))
				self.logger.info("Value of MXTMT is: {}".format(mxtmt))	
		except nvme.NVMeException as e:
			self.logger.error('Error: {}'.format(str(e)))
		
		return hctma, mntmt, mxtmt	
	
	def get_feature(self, feature_id):
		'''
		get value of specified feature
		:return: value of feature, -1 if get failed
		'''
		with self.namespace as ns:
			try:				
				if feature_id == nvme.FeatureId.HCThermMgmt:
					#self.logger.info("get current Host Controlled Thermal Management value")
					data = ns.get_hc_thermal_mgmt()
					self.logger.info("Host Controlled Thermal Management Current: 0x{:08x}".format(data))
								
			except nvme.NVMeException as e:
				self.logger.exception(e, exc_info=False)
				return -1
			
		return data
	
	def set_feature(self, feature_id, new_value):
		'''
		set value of specified feature and check if set successfully
		:return: 0 is set passed, -1 if set failed
		'''		
		try:
			with self.ctrl as c:
				before_feature_value = self.get_feature(feature_id)
				if before_feature_value == -1:
					self.logger.error("Get value of {} failed".format(feature_id))
					return -1
				else:
					#self.logger.info("Before set feature: 0x{:08x}".format(before_feature_value))
			
					self.logger.info("Set new value to: 0x{:08x}".format(new_value))
					c.set_feature(
					nsid=0,
				    feature_id=feature_id,
				    value=new_value,
				    cdw12 = 0,
				)
			
					#self.logger.info("get new value after set feature")
					new_feature_value = self.get_feature(feature_id)
					if new_feature_value == -1:
						self.logger.error("Get value of {} failed".format(feature_id))
						return -1
					else:
						#self.logger.info("New value after set feature: 0x{:08x}".format(new_feature_value))
				
						if new_value == new_feature_value:
							self.logger.info("Set feature passed: value is set")
							
						else:
							self.logger.error("Set feature failed: value is not set")
							return -1
		
		
		except nvme.NVMeException as e:
			self.logger.error("Set feature failed: value is not set")
			self.logger.error('Error: {}'.format(str(e)))	
			return -1
	
		return 0
	
	def get_smart_temperature(self):
		'''
		get current temperature from smart log
		'''
		all_smart_data = None
		temp_dict = {}
		try:
			with self.ctrl:
				all_smart_data = self.ctrl.smart_log()
				temperature = all_smart_data.temperature
				kelvin = temp_dict[temperature] = round(temperature + 273.15)
				self.logger.info('Current temperature is: {}'.format(temp_dict))
	
		except nvme.NVMeException as e:
			self.logger.error('Get temperature failed.')
			self.logger.error('Error: {}'.format(str(e)))
			return -1, -1
		return temp_dict, kelvin	
	
	
	def nvme_reset(self):
		try:
			with self.ctrl as c:
				ret = c.reset()
				self.logger.info('NVMe reset, ret: {}'.format(ret))
		except nvme.NVMeException as e:
			self.logger.error('NVMe reset failed.')
			self.logger.error('Error: {}'.format(str(e)))
			return -1
		return ret
	
	def get_current_tmt(self):
		'''
		Get current TMT values
		'''
		hctm_value = self.get_feature(nvme.FeatureId.HCThermMgmt)
		tmt2 = int(bin(hctm_value)[-16:],2)  #lower 16 bit for tmt2
		tmt1 = int(bin(hctm_value)[2:-16],2) #higher 16 bit for tmt1	
		self.logger.info('TMT1 is: {}, TMT2 is: {}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
		return tmt1, tmt2
	
	def trigger_light_throttling(self):
		'''
		Set TMT1 < T < TMT2 to trigger light throttling 
		'''
		t, kelvin = self.get_smart_temperature()

		if t == -1:
			return -1
		
		tmt1, tmt2 = self.get_current_tmt()
		if tmt1 < kelvin < tmt2:
			self.logger.info('Already in light throttling state')
			return 0, tmt1, tmt2
		
		if kelvin < self.mntmt:  #error handling, if current temp is lower then mntmt, ignore test
			self.logger.info('Current temperature is lower than mntmt, ignore this test')
			return 1
		if kelvin > self.mntmt and (kelvin - self.mntmt) <=2:
			self.logger.info('No enough gap to set TMT, ignore this test')
			return 1
		if kelvin > self.mxtmt:
			self.logger.error('Current temperature is higher than mxtmt, abort test')
			return -1

		try:
			tmt1 = random.randint(max(self.mntmt, kelvin - 2), kelvin)
			tmt2 = random.randint(kelvin + 1, self.mxtmt)	
			new_value = (tmt1 << 16) + tmt2
			self.logger.info('Set TMT1/TMT2 to value {}/{}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
			if self.set_feature(nvme.FeatureId.HCThermMgmt, new_value) != -1:
				self.logger.info('Light throttling triggered.')
				return 0, tmt1, tmt2
			else:
				self.logger.error('Light throttling trigger failed.')
				return -1
		except Exception as e:
			self.logger.error('Something wrong during light throttling: {}'.format(e))
			return -1
	
	def trigger_light_throttling_tmt1_equal(self):
		'''
		Set TMT1 = T < TMT2 to trigger light throttling 
		'''
		t, kelvin = self.get_smart_temperature()

		if t == -1:
			return -1
		
		tmt1, tmt2 = self.get_current_tmt()
		if tmt1 == kelvin < tmt2:
			self.logger.info('Already in light throttling state')
			return 0, tmt1, tmt2
		
		if kelvin < self.mntmt:  #error handling, if current temp is lower then mntmt, ignore test
			self.logger.info('Current temperature is lower than mntmt, ignore this test')
			return 1
		if kelvin > self.mxtmt:
			self.logger.error('Current temperature is higher than mxtmt, abort test')
			return -1
		try:
			tmt1 = kelvin
			tmt2 = random.randint(kelvin + 1, self.mxtmt)	
			new_value = (tmt1 << 16) + tmt2
			self.logger.info('Set TMT1/TMT2 to value {}/{}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
			if self.set_feature(nvme.FeatureId.HCThermMgmt, new_value) != -1:
				self.logger.info('Light throttling triggered.')
				return 0, tmt1, tmt2
			else:
				self.logger.error('Light throttling trigger failed.')
				return -1	
		except Exception as e:
			self.logger.error('Something wrong during light throttling: {}'.format(e))
			return -1
	
	def trigger_heavy_throttling(self):
		'''
		Set TMT1 < TMT2 < T to trigger heavy throttling 
		'''
		t, kelvin = self.get_smart_temperature()

		if t == -1:
			return -1
		
		tmt1, tmt2 = self.get_current_tmt()
		if tmt1 < tmt2 < kelvin:
			self.logger.info('Already in heavy throttling state')
			return 0, tmt1, tmt2	
		
		if kelvin <= self.mntmt:  #error handling, if current temp is lower then mntmt, ignore test
			self.logger.info('Current temperature is lower than mntmt, ignore this test')
			return 1
		if kelvin > self.mntmt and (kelvin - self.mntmt) <=3:
			self.logger.info('No enough gap to set TMT, ignore this test')
			return 1
		if kelvin > self.mxtmt:
			self.logger.error('Current temperature is higher than mxtmt, abort test')
			return -1

		try:
			tmt2 = random.randint(max(self.mntmt + 1, kelvin - 2), kelvin)	
			tmt1 = random.randint(self.mntmt, tmt2 - 1)
			new_value = (tmt1 << 16) + tmt2
			self.logger.info('Set TMT1/TMT2 to value {}/{}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
			if self.set_feature(nvme.FeatureId.HCThermMgmt, new_value) != -1:
				self.logger.info('Heavy throttling triggered.')
				return 0, tmt1, tmt2
			else:
				self.logger.error('Heavy throttling trigger failed.')
				return -1	
		except Exception as e:
			self.logger.error('Something wrong during heavy throttling: {}'.format(e))
			return -1
	
	def trigger_heavy_throttling_tmt2_equal(self):
		'''
		Set TMT1 < TMT2 = T to trigger heavy throttling 
		'''
		t, kelvin = self.get_smart_temperature()

		if t == -1:
			return -1
		
		tmt1, tmt2 = self.get_current_tmt()
		if tmt1 < tmt2 == kelvin:
			self.logger.info('Already in heavy throttling state')
			return 0, tmt1, tmt2	
		
		if kelvin < self.mntmt:  #error handling, if current temp is lower then mntmt, ignore test
			self.logger.info('Current temperature is lower than mntmt, ignore this test')
			return 1
		if kelvin > self.mxtmt:
			self.logger.error('Current temperature is higher than mxtmt, abort test')
			return -1
		try:
			tmt2 = kelvin
			tmt1 = random.randint(self.mntmt, tmt2 - 1)
			new_value = (tmt1 << 16) + tmt2
			self.logger.info('Set TMT1/TMT2 to value {}/{}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
			if self.set_feature(nvme.FeatureId.HCThermMgmt, new_value) != -1:
				self.logger.info('Heavy throttling triggered.')
				return 0, tmt1, tmt2
			else:
				self.logger.error('Heavy throttling trigger failed.')
				return -1	
		except Exception as e:
			self.logger.error('Something wrong during heavy throttling: {}'.format(e))
			return -1	
	
	def cancel_throttling(self):
		'''
		Set T < TMT1 < TMT2 to cancel throttling 
		'''
		t, kelvin = self.get_smart_temperature()

		if t == -1:
			return -1
			
		new_value = (self.tmt1 << 16) + self.tmt2
		self.logger.info('Restore TMT1/TMT2 to default value {}/{}'.format(self.kelvin_centigrade_map(self.tmt1), self.kelvin_centigrade_map(self.tmt2)))
		if self.set_feature(nvme.FeatureId.HCThermMgmt, new_value) != -1:
			self.logger.info('throttling cancelled.')
			return 0
		else:
			self.logger.error('throttling cancelled.')
			return -1	
	
	def kelvin_centigrade_map(self, kelvin):
		'''
		convert temperature from kelvin to degree centigrade
		'''
		centigrade = round(kelvin-273.15)
		degree_dic = {}
		degree_dic[kelvin] = centigrade
		return degree_dic
	
		
	def set_throttling(self, tmt1, tmt2):
		'''
		execute from main, used to set HCTM via given para
		tmt1/tmt2: temperature in degree centigrade
		'''
		tmt1 = int(float(tmt1) + 273.15)
		tmt2 = int(float(tmt2) + 273.15)
		new_value = (tmt1 << 16) + tmt2
		self.logger.info('Set TMT1/TMT2 to value {}/{}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
		if self.set_feature(nvme.FeatureId.HCThermMgmt, new_value) != -1:
			self.logger.info('Value set.')
			return 0
		else:
			self.logger.error('Value set failed.')
			return -1			
	
	def get_feature_tmt(self):
		'''
		get tmt value in degree centigrade
		'''
		hctm_value = self.get_feature(nvme.FeatureId.HCThermMgmt)
		tmt2 = int(bin(hctm_value)[-16:],2)  #lower 16 bit for tmt2
		tmt1 = int(bin(hctm_value)[2:-16],2) #higher 16 bit for tmt1	
		self.logger.info('TMT1 is: {}, TMT2 is: {}'.format(self.kelvin_centigrade_map(tmt1), self.kelvin_centigrade_map(tmt2)))
	
	def run_marvo_perf(self, marvo_tool_directory):
		'''
		Start marvo test to used for IO verification
		'''
		current_path = os.path.dirname(__file__)
		testcase_path = 'Background_IO'
		
		subprocess.call(["cp", "-r", testcase_path, marvo_tool_directory])
		os.chdir(marvo_tool_directory)
		process = subprocess.Popen(["sudo", "xvfb-run", "-a", "sh", \
		                            os.path.join(marvo_tool_directory, "marvo_test.sh"), \
		                            (testcase_path + "/scripts/" + "Drive_1_TestPlan.xml")], \
		                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		os.chdir(current_path)
		while (process.poll() == None):  #marvo is running, otherwise, the thread will exit after start marvo
			continue
	
	def check_thread_status(self, thread, count):
		'''
		check the background io thread status every 3 seconds for $count times
		'''
		for i in range(1, count):
			time.sleep(3)
			if (thread.isAlive() == False):
				self.logger.error('Marvo IO error occur, test failed')
				return -1
		return 0
	
	def get_IOPS_30s(self):
		'''
		Store result of last 30 seconds to temp file test and get the average IOPS
		'''
		os.system('tail -n 30 ' + self.runtime_perf_log+ ' > test')
		with open('test', 'r') as f:
			sum = 0
			lines = f.readlines()
			for line in lines:
				if 'PERF' not in line or 'IOPS' not in line:
					continue
				temp = line.split(',')[1].lstrip().rstrip().rstrip('IOPS')
				sum += int(temp)
			iops = int(sum / 30)
		self.logger.info('30 seconds average IOPS is: {}'.format(iops))
		return iops
	
if __name__ == "__main__":
	
	test = Thermal_Throttling('test.log')
	#import sys
	#if len(sys.argv) != 3:
		#sys.exit()
	#else:
		#result = test.set(sys.argv[1], sys.argv[2])
	
	iops = test.check_perf_drop()
	print('iops is: {}'.format(iops))
	
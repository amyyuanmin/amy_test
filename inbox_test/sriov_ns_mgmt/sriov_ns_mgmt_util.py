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
import os, time
import subprocess
import threading
import random
import sys
sys.path.append("../")
from common import util

config_file = "./sriov_ns_mgmt_cfg.txt"

def parse_config(item):
	return util.parse_config(config_file, "sriov_ns_mgmt", item)

def get_pci_addr_list():
	'''
	Get pci addr of the nvme device
	'''
	pci_addr_list = util.get_pci_addr_list()
	return pci_addr_list

def execute_cmd(cmd, timeout, out_flag = False, expect_fail = False, expect_err_info = None):
	'''
	Execute cmd in #timeout seconds
	out_flag: True means return cmd out(a str list), Flase not.
	expect_fail: for some error inject scenario, set this to True
	expect_err_info: if expect failure, then check the error msg as expected or not
	This comes before util.execute_cmd, a lot of reference need to be adjusted, and currently no need to change to that.
	'''
	logging.debug(cmd)
	result = 0
	try:
		p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell = True) 
		t_beginning = time.time()
		seconds_passed = 0 
		out = []
		while True:
			if p.poll() is not None: 
				out = p.stdout.readlines()
				out = [i.decode().strip("\n") for i in out]  # convert to string
				if p.returncode == 0:
					logging.debug("Cmd executed successfully")
				elif p.returncode != 1:  # specified scenario: nvme list | grep nvme, if nothing returned, the returncode is 1, it seems caused by the grep, for ex. ls | grep leon, if nothing found, returncode is 1
					logging.debug("Cmd output: {}".format(out[0]))  # just show the first out to avoid too many logs
					if expect_fail:
						logging.debug("Cmd executed failed, but it's as expected")
						result = 0
						if expect_err_info != None and expect_err_info not in out[0]:
							logging.warning("Error msg not as expected, you may have a check")
					else:
						logging.error("Cmd executed failed")
						result = -1
				break 
			time.sleep(1)
			seconds_passed = time.time() - t_beginning 
			if seconds_passed > timeout: 
				p.stdout.close()
				p.terminate()
				logging.error('Cmd not end as expected in {} seconds, terminate it'.format(timeout))
				result = -1
				break
		p.stdout.close()
	except Exception as e:
		logging.error("Cmd execution failed: {}".format(e))
		result = -1
	if out_flag == False:
		return result
	else:
		return result, out

def enable_sriov(vf_amount):
	'''
	Enable SRIOV with #vf_amount VF, if vf_amount=0 means disable all VF
	Timeout to 10 seconds
 	Check if expected VF enabled
	return 0 on success
	real amount or -1 on fail
	'''
	max_vf_amount = int(parse_config("max_vf_amount"))
	result = util.enable_sriov(vf_amount, max_vf_amount)
	
	return result

def ns_create(ctrl, ns_size, ns_cap, flb_setting=1, dps=0, nmic=0):
	return util.ns_create(ctrl, ns_size, ns_cap, flb_setting, dps, nmic)

def ns_attach(ns_id, ctrl_list):
	return util.ns_attach(ns_id, ctrl_list)

def ns_detach(ns_id, ctrl_list, expect_fail = False):
	return util.ns_detach(ns_id, ctrl_list, expect_fail)

def rescan_ctrl(ctrl_list):
	return util.rescan_ctrl(ctrl_list)

def ns_delete(ctrl, ns_id, expect_fail = False):
	return util.ns_delete(ctrl, ns_id, expect_fail)

def format_ns(ns, ns_id, lbaf=1, erase=0):
	return util.format_ns(ns, ns_id, lbaf, erase)

def ns_mgmt_cases(ns_amount, shared_flag = 0, flbaf_list = [1]):
	'''
	flbaf_list: default is 1, if set to a list, then each config with a flbaf.
	'''
	return util.ns_mgmt_cases(ns_amount, shared_flag, flbaf_list)

def ns_mgmt_basic(shared_flag = 0):
	tests = []

	tests.append({'controller': '/dev/nvme0', 'size': 0x20000, 'capacity': 0x20000, 'flba': 1, 'dps': 0, 'shared': shared_flag})
	
	return tests

def spread_nonshared_ns_to_ctrl(ns_amount, ctrl_amount, method = 'even'):
	'''
	spread created NS to controllers
	method: random or even
	'''
	amount_list = []  # a list of amount for each controller
	if method == 'even':
		amount_single = int(ns_amount / ctrl_amount)
		amount_left = ns_amount % ctrl_amount  # ns left after divided
		if amount_single == 0:
			for i in range(0, ns_amount):
				amount_list.append(1)  # if ns amount is less than ctrl amount, spread 1 ns to 1 ctrl till all ns used up
		else:
			for i in range(0, ctrl_amount):    			
				amount_list.append(amount_single)
			if amount_left != 0:
				for i in range(0, amount_left):
					amount_list[i] += 1  
	
	elif method == 'random':
		if ns_amount <= ctrl_amount:
			for i in range(0, ns_amount):
				amount_list.append(1)  # if ns amount is less than ctrl amount, spread 1 ns to 1 ctrl till all ns used up
		else:
			amount_temp = 0
			ctrl_amount_temp = ctrl_amount
			for i in range(0, ctrl_amount):
				amount_temp = random.randint(1, int((ns_amount - ctrl_amount_temp + 1) / (ctrl_amount / 2)))
				ns_amount -= amount_temp
				ctrl_amount_temp -= 1
				amount_list.append(amount_temp)
			amount_list.append(ns_amount)

	logging.info("NS amount list for controllers: {}".format(amount_list))
	return amount_list

def spread_shared_ns_to_ctrl(ns_amount, ctrl_amount):
	'''
	spread created NS to controllers
	'''
	amount_list = []  # a list of amount for each controller
	for i in range(0, ctrl_amount): # all ns to each ctrl
		amount_list.append(ns_amount)

	logging.info("NS amount list for controllers: {}".format(amount_list))
	return amount_list

def fio_on_ns(ns_str, log_folder = os.getcwd(), io_type = "mix", size = "50%", qd = "16"):
	'''
	ns_str: example - /dev/nvme0n1 /dev/nvme10n0
	io_type: read, write, or conbination of each. Read used mix RW workload 
	'''
	io_cfg = parse_config("io_cfg")
	log_str = ns_str.strip("/dev/")
	seqwr_log = os.path.join(log_folder, "seqwr_{}.log".format(log_str))
	seqrd_log = os.path.join(log_folder, "seqrd_{}.log".format(log_str))
	seqrw_log = os.path.join(log_folder, "seqrw_{}.log".format(log_str))
	seqwr_cmd = "sudo SIZE={} fio {} --filename={} --section=seqwr_32k_iodepth_16 --output={}".format(size, io_cfg, ns_str, seqwr_log)
	seqrd_cmd = "sudo SIZE={} QD={} fio {} --filename={} --section=seqrd_32k_iodepth_16 --output={}".format(size, qd, io_cfg, ns_str, seqrd_log)
	seqrw_cmd = "sudo SIZE={} fio {} --filename={} --section=write_50_to_100 --section=read_0_to_50 --output={}".format(size, io_cfg, ns_str, seqrw_log)

	timeout = int(parse_config("timeout"))
	if "write" in io_type:
		execute_cmd(seqwr_cmd, timeout)
	time.sleep(5) # to avoid limitation of write cache, i.e. only read from flash is availabe, cannot read from write cache
	if "read" in io_type:
		execute_cmd(seqrd_cmd, timeout)
	if "mix" in io_type:
		execute_cmd(seqrw_cmd, timeout)
	time.sleep(5)

	return seqwr_log, seqrd_cmd, seqrw_log

def run_io_on_namespaces(ns_list, log_folder = os.getcwd(), io_type = "mix", size = "50%", qd = "16", number_to_be_tested = "all"):
	'''
	Run fio on multiple NS at the same time
	vail_mix: new added based on NS write limitation, i.e. only allow write at one NS at one time.
	number_to_be_tested: how many NS that IO to be issued on. 
	Since if too many FIO processes run at the same time, might result in OOM on OS.
 	'''
	thread_list = []
	ns_list_test = []
	if number_to_be_tested == "all":
		ns_list_test = ns_list
	else:
		for i in range(0, int(number_to_be_tested)):
			ns_list_test.append(ns_list[random.randint(0, len(ns_list))])
	ns_list_test = list(set(ns_list_test))  # incase duplicated NS selected
	for ns_str in ns_list_test:
		if io_type == "vail_mix":
			io_type = "read"
		t = threading.Thread(target=fio_on_ns, args=(ns_str, log_folder, io_type, size, qd))
		t.start()
		thread_list.append(t)

	# Below if section work executed, not sure why
	if io_type == "vail_mix":
		for ns_str in ns_list:
			fio_on_ns(ns_str, log_folder, "mix", size, qd)

	for t in thread_list:
		t.join(timeout = 300)

def check_fio_result(log_file, pattern = "err="):
	result = util.check_fio_result(log_file=log_file, pattern=pattern, eliminate_log=True)
	return result

def check_identify_values(device, item, expected = None):
	'''
	device: controller or ns, to determin which nvme cmd used
	item: item to be checked
	expected: expected value of this item
	'''
	logging.debug("Checking identify item: {}".format(item))
	result = "Failed"
	real_value = None
	real_value = get_specified_id_value(device, item)
	if real_value == -1:
		return "Failed"

	if expected != None:
		logging.debug("Expected value of {} is {}".format(item, expected))
		if real_value == expected:
			result = "Passed"
		else:
			logging.error("Real value of {} is {}, expected: {}".format(item, real_value, expected))
	
	# below for some specified items
	else:
		if item.upper() == "OACS":
			if int(real_value, 16) & (1 << 3) != 0:  # bit 3
				result = "Passed"
			else:
				logging.error("The bit 3 of OACS should be 1")
	if result == "Failed":
		logging.error("Check value of {} not as expected".format(item))
	logging.debug("Check result: {}".format(result))
	return result

def get_specified_id_value(device, item):
	return util.get_specified_id_value(device, item)

def check_nvmcap(ctrl):
	'''
	Just used to do compare of TNVMCAP and UNVMCAP
	'''
	result = "Failed"
	tnvmcap = int(get_specified_id_value(ctrl, "TNVMCAP"))
	unvmcap = int(get_specified_id_value(ctrl, "UNVMCAP"))
	if tnvmcap == 0 or unvmcap == 0:
		logging.error("The value of TNVMCAP and UNVMCAP should not be 0")
	elif tnvmcap >= unvmcap:
		result = "Passed"
	else:
		logging.error("TNVMCAP should not less than UNVMCAP")
	
	return result

def check_flbaf(ns, expected_lbaf):
	'''
	check identify values after format LBAF
	'''
	result = "Failed"
	flbas = get_specified_id_value(ns, "flbas")

	id_cmd = "nvme id-ns {} | grep 'in use'".format(ns)
	ret, id_value = execute_cmd(id_cmd, 10, True)
	logging.debug("Output: {}".format(id_value))
	
	if id_value[0].split(":")[0].strip("lbaf").strip() == expected_lbaf:
		if int(expected_lbaf) == 0 and flbas == "0":
			result = "Passed"
		elif hex(int(expected_lbaf)) == flbas:
			result = "Passed"
		else:
			logging.error("flbas value incorrect, real: {}, expected: {}".format(flbas, expected_lbaf))
	else:
		logging.error("flbas value incorrect, real: {}, expected: {}".format(flbas, expected_lbaf))
	
	return result

def check_get_real_ns():
	'''
	check if NS really detected after attach and get the real NS name if detected
	Issue: The ctrl id and the real number in controllers might not be the same
	(for ex, id is 21, the controller might show as /dev/nvme20, doubtful, need to check with a third party drive)
	Return: all detected NS list
	'''
	return util.check_get_real_ns()

def check_fio_logs(fio_log_folder, except_key = None):
	'''
	Check result of all FIO logs under fio_log_folder
	except_key: all FIO logs without except_key in file name.
	'''
	util.check_fio_logs(fio_log_folder=fio_log_folder, except_key=except_key, eliminate_log=True)

if __name__ == "__main__":
	# ns_mgmt_cases(32, shared_flag = 0, flba_list = [1])

	# ns_mgmt_cases(12, shared_flag = 0, flba_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

	# ns_mgmt_cases(32, shared_flag = 0, flba_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
	#spread_nonshared_ns_to_ctrl(33, 1)
	ns_list = ["/dev/nvme0n1"]
	run_io_on_namespaces(ns_list, log_folder = os.getcwd(), io_type = "vail_mix", size = "50%")
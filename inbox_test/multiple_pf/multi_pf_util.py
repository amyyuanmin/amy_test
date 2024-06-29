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
from configparser import RawConfigParser

config_file = "./multi_pf_cfg.txt"

def parse_config(item):
	config = RawConfigParser()
	config.read(config_file)

	item_value = config.get('multi_pf', item).strip()
	if "," in item_value:
		item_value = item_value.split(",")
	
	return item_value

def get_pci_addr_list():
	'''
	Get pci addr of the nvme device
	'''
	cmd = "lspci -D | grep 'Non-Volatile memory' | grep 'Marvell' | grep -o '....:..:....'"
	ret, pci_addr_list = execute_cmd(cmd, 10, out_flag = True)
	logging.info("PCI addr list: {}".format(pci_addr_list))
	return pci_addr_list

def execute_cmd(cmd, timeout, out_flag = False, expect_fail = False, expect_err_info = None):
	'''
	Execute cmd in #timeout seconds
	out_flag: True means return cmd out(a str list), Flase not.
	expect_fail: for some error inject scenario, set this to True
	expect_err_info: if expect failure, then check the error msg as expected or not
	'''
	logging.info(cmd)
	result = 0
	try:
		p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell = True) 
		t_beginning = time.time()
		seconds_passed = 0 
		while True:
			if p.poll() is not None: 
				out = p.stdout.readlines()
				out = [i.decode().strip("\n") for i in out]  # convert to string
				if p.returncode == 0:
					logging.info("Cmd executed successfully")
				elif p.returncode != 1:  # specified scenario: nvme list | grep nvme, if nothing returned, the returncode is 1, it seems caused by the grep, for ex. ls | grep leon, if nothing found, returncode is 1
					logging.info("Cmd output: {}".format(out[0]))  # just show the first out to avoid too many logs
					if expect_fail:
						logging.info("Cmd executed failed, but it's as expected")
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
				if "fio" in cmd:
					os.system("pkill -9 fio")
				p.terminate()
				logging.info('Cmd not end as expected in {} seconds, terminate it'.format(timeout))
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

def check_get_pf(pf_amount):
	'''
	Check if expected PF exists
	return 0 on success
	real amount or -1 on fail
	'''
	pci_addr_list = get_pci_addr_list()
	real_amount = len(pci_addr_list)
	real_ns_list = get_all_ns()
	if real_amount == 0 or real_ns_list == []:
		logging.error("No controllers or namespace found")
		return -1
	elif real_amount != pf_amount or len(real_ns_list) != pf_amount:
		logging.error("Found {} controllers, {} namespaces, expected: {}".format(real_amount, len(real_ns_list), pf_amount))
		return -1
	else:
		logging.info("Expected {} controllers/namespaces found".format(real_amount))
		
	return real_ns_list

def fio_on_ns(ns_str, offset = 0, size = "100%", log_folder = os.getcwd(), io_type = 'mix', readsize="100%"):
	'''
	ns_str: example - /dev/nvme0n1 /dev/nvme10n1
	offset: due to E2E limitation, issue write to different range, for mix scenario, offset/size only works for write, read already specified in .fio cfg
	io_type: read, write, or conbination of each. Read used mix RW workload 
	readsize: only used for read in mixed traffic 
	'''
	io_cfg = parse_config("io_cfg")
	log_str = ns_str.strip("/dev/")
	wr_log = os.path.join(log_folder, "wr_{}.log".format(log_str))
	rw_log = os.path.join(log_folder, "rw_{}.log".format(log_str))
	rd_log = os.path.join(log_folder, "rd_{}.log".format(log_str))

	wr_cmd = "sudo SIZE={} OFFSET={} fio {} --filename={} --section=seqwr_128k_iodepth_32 --output={}".format(size, offset, io_cfg, ns_str, wr_log)
	rw_cmd = "sudo SIZE={} OFFSET={} READSIZE={} fio {} --filename={} --section=write --section=read --output={}".format(size, offset, readsize, io_cfg, ns_str, rw_log)
	rd_cmd = "sudo SIZE={} OFFSET={} fio {} --filename={} --section=verify_read --output={}".format(size, offset, io_cfg, ns_str, rd_log)

	timeout = int(parse_config("timeout"))
	if "write" in io_type:
		execute_cmd(wr_cmd, timeout)
	time.sleep(5) # to avoid limitation of write cache, i.e. only read from flash is availabe, cannot read from write cache
	if "read" in io_type:
		execute_cmd(rd_cmd, timeout)
	if "mix" in io_type:
		execute_cmd(rw_cmd, timeout)
	time.sleep(5) # to avoid limitation of write cache

	return wr_log, rw_log, rd_log

def run_io_on_namespaces(ns_list, offset_overall = 0, size_overall = "100%", log_folder = os.getcwd(), io_type = "mix", split_flag = True, readsize="100%"):
	'''
	Run fio on multiple NS at the same time
	Due to limitation that no overwrite allowed, offset_overall/size_overall determine the whole range for all NS, support % or g(both at the same unit), only exeception is 0, can be only 0 without unit.
	split_flag: split offset/size to NSs, if False, all use the same offset/size
	'''
	thread_list = []
	if split_flag:
		size_num = int(size_overall[:-1]) // len(ns_list)
		size = str(size_num) + size_overall[-1]
	else:
		size = size_overall
	for ns_str in ns_list:
		if split_flag:
			if offset_overall != 0:
				offset = str(int(offset_overall[:-1]) + ns_list.index(ns_str) * size_num) + offset_overall[-1]
			else:
				offset = str(ns_list.index(ns_str) * size_num) + size_overall[-1]
		else:
			offset = offset_overall
		t = threading.Thread(target=fio_on_ns, args=(ns_str, offset, size, log_folder, io_type, readsize,))
		t.start()
		thread_list.append(t)
	for t in thread_list:
		t.join()

def check_fio_result(log_file, pattern = "err="):
	logging.info("Checking fio result: {}".format(log_file))
	result = 'Pass'
	flag = 0  # if no err= info in output file
	if os.path.exists(log_file):
		with open(log_file, 'r') as processLog:
			while True:
				entry = processLog.readline()
				if pattern in entry:
					flag = 1
					if pattern + " 0" in entry:
						logging.info("FIO test passed")
						result = "Pass"  # there might be several result, for ex. Mixed RW
					else:
						logging.info("FIO test failed")
						result = "Fail"
						break
				elif entry == '':
					if flag == 0:
						logging.info("No result info found, FIO test failed")
						result = "Fail"
					break
	else:
		logging.error("No fio log found:{}".format(log_file))
		result = "Fail"
	return result

def get_all_ns():
	'''
	Get all available NS, one on each PF as designed
	'''
	ns_list = []
	list_cmd = "nvme list | grep nvme"
	ret, out = execute_cmd(list_cmd, 10, out_flag = True)
	# out ex: ['/dev/nvme0n1     S41FNX0M117868       SAMSUNG MZVLB256HAHQ-000L2               1         256.06  GB / 256.06  GB    512   B +  0 B   0L1QEXD7']
	if out == []:
		logging.error("No NS found")
	else:
		for item in out:
			ns = item.split(" ")[0].strip()
			ns_list.append(ns)
	logging.info("NS list: {}".format(ns_list))
	return ns_list

def get_specified_id_value(device, item):
	'''
	Get the value of specified identify item
	'''
	if "n" in device.strip("/dev/nvme"): # indicate NS
		id_cmd = "nvme id-ns {}".format(device)
	else:
		id_cmd = "nvme id-ctrl {}".format(device)
	ret, id_value = execute_cmd(id_cmd, 10, True)

	for value in id_value:
		if item.lower() in value:
			real_value = value.split(":")[1].strip()
			logging.info("Real value of {} is {}".format(item, real_value))
			return real_value
	else:
		logging.warning("No item {} found".format(item))
		return -1
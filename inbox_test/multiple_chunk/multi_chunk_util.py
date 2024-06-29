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
from configparser import ConfigParser

config_file = "./multi_chunk_cfg.txt"

def parse_config(item):
	config = ConfigParser()
	config.read(config_file)

	item_value = config.get('multi_chunk', item).strip()
	if "," in item_value:
		item_value = item_value.split(",")
	
	return item_value

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

def fio_on_ns(ns_str, offset = 0, size = "100%", log_folder = os.getcwd(), io_type = 'mix', bs = "128k", test = "basic"):
	'''
	ns_str: example - /dev/nvme0n1 /dev/nvme10n1
	offset: due to E2E limitation, issue write to different range, for mix scenario, offset/size only works for write, read already specified in .fio cfg
	io_type: read, write, or conbination of each. Read used mix RW workload 
	bs: block size for test
	test: basic or stress, to specify the test section
	'''
	io_cfg = parse_config("io_cfg")
	wr_log = os.path.join(log_folder, "wr_{}.log".format(bs))
	rw_log = os.path.join(log_folder, "rw_{}.log".format(bs))
	rd_log = os.path.join(log_folder, "rd_{}.log".format(bs))
	
	section_wr = "write_{}".format(test)
	section_rd = "read_{}".format(test)

	wr_cmd = "sudo SIZE={} OFFSET={} BS={} fio {} --section={} --output={}".format(size, offset, bs, io_cfg, section_wr, wr_log)
	rw_cmd = "sudo SIZE={} OFFSET={} BS={} fio {} --section={} --section={} --output={}".format(size, offset, bs, io_cfg, section_wr, section_rd, rw_log)
	rd_cmd = "sudo SIZE={} OFFSET={} BS={} fio {} --section={} --output={}".format(size, offset, bs, io_cfg, section_rd, rd_log)

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
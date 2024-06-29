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

import sys
import os
import time
sys.path.append("../")
from common import util

cfg_file = "reset.cfg"
section = "reset"

def test_multi_ns_preparation(func_amount):
    util.basic_multi_ns_setup(func_amount=int(func_amount))
    
def fio_on_ns(ns_str, offset = 0, size = "100%", log_folder = os.getcwd(), io_type = 'mix', readsize="100%"):
	'''
	ns_str: example - /dev/nvme0n1 /dev/nvme10n1
	offset: due to E2E limitation, issue write to different range, for mix scenario, offset/size only works for write, read already specified in .fio cfg
	io_type: read, write, or conbination of each. Read used mix RW workload 
	readsize: only used for read in mixed traffic 
	'''
	io_cfg = util.parse_config(cfg_file, section, "io_cfg")
	log_str = ns_str.strip("/dev/")
	wr_log = os.path.join(log_folder, "wr_{}.log".format(log_str))
	rw_log = os.path.join(log_folder, "rw_{}.log".format(log_str))
	rd_log = os.path.join(log_folder, "rd_{}.log".format(log_str))

	wr_cmd = "sudo SIZE={} OFFSET={} fio {} --filename={} --section=seqwr_128k_iodepth_32 --output={}".format(size, offset, io_cfg, ns_str, wr_log)
	rw_cmd = "sudo SIZE={} OFFSET={} READSIZE={} fio {} --filename={} --section=write --section=read --output={}".format(size, offset, readsize, io_cfg, ns_str, rw_log)
	rd_cmd = "sudo SIZE={} OFFSET={} fio {} --filename={} --section=verify_read --output={}".format(size, offset, io_cfg, ns_str, rd_log)

	timeout = int(util.parse_config(cfg_file, section, "timeout"))
	if "write" in io_type:
		util.execute_cmd(wr_cmd, timeout)
	time.sleep(5) # to avoid limitation of write cache, i.e. only read from flash is availabe, cannot read from write cache
	if "read" in io_type:
		util.execute_cmd(rd_cmd, timeout)
	if "mix" in io_type:
		util.execute_cmd(rw_cmd, timeout)
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
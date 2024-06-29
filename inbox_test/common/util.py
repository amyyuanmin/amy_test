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
import re
import pytest
from sfvs.nvme import nvme
from .fvt_adm_cmd_common import fvt_adm
from configparser import ConfigParser
import random
    
def execute_cmd(cmd, timeout = 10, out_flag = False, expect_fail = False, expect_err_info = None, extra_key = None, expected_key = None, eliminate_log = False):
    '''
    Execute cmd in #timeout seconds
    out_flag: True means return cmd out(a str list), Flase not.
    expect_fail: for some error inject scenario, set this to True
    expect_err_info: if expect failure, then check the error msg as expected or not, might be a string or list of error
    extra_key: some key info might be used, for ex. currently for fio t-put check, need the NS info 
    expected_key: if cmd executed successfully, check if some specified keyword in output
    eliminate_log: sometimes we want to avoid too many logs
    return: result 0 if pass, -1 for fail; out - output in a list of string

    '''
    if not eliminate_log:
        logging.info(cmd)
    result = 0
    out = None
    # cmd = shlex.split(cmd)
    try:
        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell = True) 
        t_beginning = time.time()
        seconds_passed = 0 
        if "dmesg" in cmd:  # for dmesg cmd, the output might fulfill the buffer, thus p.poll will always waiting
            out = p.stdout.readlines()
        while True:
            if p.poll() is not None: # cmd executed successfully
                out = p.stdout.readlines()
                out = [i.decode().strip("\n") for i in out]  # convert to string
                logging.debug("Out of execute_cmd: {}".format(out))
                if p.returncode == 0:
                    if not eliminate_log:
                        logging.info("Cmd executed successfully")
                    if expected_key != None:
                        for item in out:
                            if expected_key in item:
                                break
                        else:
                            if not eliminate_log:
                                logging.warning("No expected info found at output")
                            result = -1
                elif p.returncode != 1:  # specified scenario: nvme list | grep nvme, if nothing returned, the returncode is 1, it seems caused by the grep, for ex. ls | grep leon, if nothing found, returncode is 1
                    if not eliminate_log:
                        logging.info("Cmd output: {}".format(out[0]))  # just show the first out to avoid too many logs
                    if expect_fail:
                        if not eliminate_log:
                            logging.info("Cmd executed failed, but it's as expected")
                        result = 0
                        if expect_err_info != None:
                            if type(expect_err_info) == list:
                                for expect_err in expect_err_info:
                                    if expect_err not in out[0]:
                                        continue
                                    else:
                                        break
                                else:
                                    logging.error("Error msg not as expected, you may have a check")
                                    result = -1
                            else:
                                if expect_err_info not in out[0]:
                                    logging.error("Error msg not as expected, you may have a check")
                                    result = -1
                    else:
                        if not eliminate_log:
                            logging.error("Cmd executed failed")
                        result = -1
                break 
            time.sleep(0.5)
            seconds_passed = time.time() - t_beginning 
            if seconds_passed > timeout: 
                p.stdout.close()
                if "fio" in cmd:
                    # after timeout, check t-put to determin if IO still running, to avoid IO stopped unexpectedly due to too small timeout value
                    while True:
                        if check_tput(extra_key):
                            break
                        time.sleep(60)
                        timeout += 60
                    os.system("pkill -9 fio")
                p.terminate()
                logging.info('Cmd not end as expected in {} seconds, terminate it'.format(timeout))
                result = -1
                break
        p.stdout.close()
    except Exception as e:
        logging.error("Cmd execution failed: {}".format(e))
        logging.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        result = -1
    if out_flag == False:
        return result
    else:
        return result, out
    
def check_tput(ns_str):
    '''
    Simple way to check the tput on a device, currently used to check if FIO still run normally, i.e. t-put not all 0
    ns_str: device name, i.e. nvme0n1
    return: True if no IO running
    '''
    logging.info("Check t-put to determin if IO still ongoing")
    check_cmd = "iostat -d 2 -c 5 | grep {}".format(ns_str)
    ret, out = execute_cmd(check_cmd, 15, out_flag = True)
    for item in out:
        if out.index(item) != 0:
            temp = re.sub('\\s', '', item)[len(ns_str):]  # if FIO run stopped, all t-put values should be 0
            check_str = "123456789"
            if any(i in check_str for i in temp):
                logging.info("IO still running")
                time.sleep(120)
                return False
    logging.info("No IO running")
    return True

def fio_runner(io_cfg = "basic_io.fio", section = "basic_io", ns_str = "/dev/nvme0n1", io_engine = "libaio", io_type = "write", size = "100%", 
                   bs = "128k", offset = 0, q_depth = 32, thread = 1, pattern = "0x55aa55aa", runtime = 0, time_based = 1,
                   log_folder = os.getcwd(), log_str = "fio_result.log", timeout = 60, expected_failure = None, check_result = True):
    '''
    Start a fio process
    io_engin: libaio or iouring(usually for performance)
    io_type: for ex. sequential write(write), sequential read(read), random write(randwrite), random read(randread)
    size: size of IO
    bs: io size of each write
    log_folder: where the fio log stored, for record and result analysis
    timeout: timeout for if IO still running check
    runtime: runtime argument for fio
    time_based: if time_based, always run specified runtime, otherwise, will stop either IO finished on SIZE or runtime
    expected_failure: for some scenario that expect specified error, for ex. AES test expect mismatch(err=84) error after read out encrypted data
    check_result: if check result after fio. Flase usually for threading, since if in thread, pytest.fail not work
    '''
    log_str = os.path.join(log_folder, log_str)
    # Workaround for Vail SDK, if MCOD not enabled, it costs 3s for FTL flush after write, thus verify when write is not possible
    verify = 1
    if "write" in io_type:
        verify = 0
    io_cfg = os.path.join(os.path.split(os.path.realpath(__file__))[0], io_cfg)
    io_cmd = "sudo IOENGINE={} SIZE={} OFFSET={} IOTYPE={} BS={} QD={} THREAD={} NS={} RUNTIME={} TIMEBASED={} VERIFY={} PATTERN={} fio {} --section={} --output={}"\
                .format(io_engine, size, offset, io_type, bs, q_depth, thread, ns_str, runtime, time_based, verify, pattern, io_cfg, section, log_str)
    
    if expected_failure == None:
        execute_cmd(io_cmd, timeout = timeout, extra_key=ns_str.strip("/dev/"))
        if check_result:        
            if check_fio_result(log_str) == "Fail":
                logging.error("FIO test failed")
                pytest.fail("FIO test failed")  # abort test or not?
    else:
        execute_cmd(io_cmd, timeout = timeout, expect_fail=True, extra_key=ns_str.strip("/dev/"))
        if check_result:
            if check_fio_result(log_str, expected_error=expected_failure) == "Fail":
                logging.error("No expected error: {} found".format(expected_failure))
                pytest.fail("No expected error found")
    
    return log_str
    
def check_fio_result(log_file, pattern = "err=", expected_error = " 0", eliminate_log = False):
    '''
    expected_error: if it's an error code(check with length <4), adopt pattern err=, otherwise, just check expected error.
    Usually fio report result with err=error_code, 0 means pass, 84 means miscompare.
    But sometimes in practice for example, if miscompare met, err=84 not in report.
    eliminate_log: sometimes, there'll be too many FIO log to be checked(for ex, SRIOV), we want to avoid console output.
    '''
    result = 'Fail'
    if not eliminate_log:
        logging.info("Checking FIO result on result file:{}".format(log_file))
    else:
        logging.debug("Checking FIO result on result file:{}".format(log_file))
    if os.path.exists(log_file):
        if os.path.getsize(log_file) == 0:
            logging.error("Result log is empty")
        else:
            if len(expected_error.strip()) >= 4: # if match with not error code
                pattern = ""
            with open(log_file, 'r') as processLog:
                while True:
                    entry = processLog.readline()                
                    if pattern + expected_error in entry:
                        if expected_error != " 0":
                            logging.info("Check FIO result successfully, FIO test passed, found expected result: {}".format(pattern + expected_error))
                        else:
                            if not eliminate_log:
                                logging.info("Check FIO result successfully, FIO test passed")
                            else:
                                logging.debug("Check FIO result successfully, FIO test passed")
                        result = "Pass"  # there might be several result, for ex. Mixed RW
                        break
                    elif entry == "": # reach the end
                        logging.error("No expected result found on fio report: {}, FIO test failed".format(log_file))
                        break
                    
    else:
        logging.error("No fio log found:{}".format(log_file))
    return result

def check_fio_logs(fio_log_folder = None, result_logs = None, except_key = None, eliminate_log = False):    
    '''
    Check result of all FIO logs under fio_log_folder
    fio_log_foler/result_logs: this two are exclussive, check all logs under log or just check some logs
    except_key: all FIO logs without except_key in file name.
    '''
    logging.info("Check all FIO results")
    if fio_log_folder != None and result_logs != None:
        logging.error("Exclusive argument, please correct")
        pytest.exit("Exclusive argument, please correct")
    fio_logs = []
    if fio_log_folder != None:    
        for root, dirs, files in os.walk(fio_log_folder):
            for file in files:
                if os.path.splitext(file)[1] == '.log':  
                    fio_logs.append(os.path.join(root, file))  

    elif result_logs != None:
        fio_logs = result_logs
    for log in fio_logs:
        if except_key == None:
            if check_fio_result(log, eliminate_log=eliminate_log) != "Pass":
                logging.error("FIO test failed, log file: {}".format(log))
                pytest.fail("FIO test failed, log file: {}".format(log))
        elif except_key != None and except_key not in log and check_fio_result(log, eliminate_log=eliminate_log) != "Pass":
            logging.error("FIO test failed, log file: {}".format(log))
            pytest.fail("FIO test failed, log file: {}".format(log))

def get_latency(log_file):
    '''
    Get average completion latency from fio result log, unify unit to us
    '''
    result_line = None
    with open(log_file, 'r') as file:
        while True:
            out = file.readline()
            if not out:
                break
            else:
                if "avg" in out and "clat" in out:
                    result_line = out.strip()
                    #example: clat (usec): min=2706, max=12829, avg=6221.10, stdev=2548.43
                    logging.info("Found result line: {}".format(result_line))
                    break
    
    if result_line == None:
        logging.error("No expected result info found")
        pytest.fail("No expected result info found")
    else:
        pattern = "^clat \\(([um]?sec)\\):.*avg=(.*),.*$"
        result = re.match(pattern, result_line)
        convert_table = {"msec": 1000, "usec": 1, "sec": 1000000}
        convert_rate = convert_table[result.group(1)]
        result_value = int(float(result.group(2)) * convert_rate)
        
        logging.info("Average latency is: {}us".format(result_value))
    return result_value

def ssh_cmd(cmd, remote_ip, username = "pi", password = "123456", out_flag = False, eliminate_log = False):
    '''
    Execute cmd on remote via sshpass
    note: out - ["Warning: Permanently added '10.25.151.64' (ECDSA) to the list of known hosts.\r", '0']
    There always be Warning recorded, no idea why, so need to ignore the out[0]
    '''
    if ("scp" not in cmd) and ("rsync" not in cmd):
        common_cmd = "sshpass -p {} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null".format(password)

        full_cmd = "{} {}@{} {}".format(common_cmd, username, remote_ip, cmd)
    else:
        common_cmd = "sshpass -p {}".format(password)
        full_cmd = "{} {}".format(common_cmd, cmd)
        
    ret = execute_cmd(full_cmd, out_flag = out_flag, eliminate_log=eliminate_log)
    if out_flag and len(ret[1]) > 1:
        out = ret[1][1]
    else:
        out = None
    return ret, out

def nvme_format(format_lbaf, ses=0, pi=0):
    '''
    Format drive to specified LBAF
    '''
    logging.info("Format to LBAF: {}".format(format_lbaf))
    host = nvme.Host.enumerate()[0]
    controller = host.controller.enumerate()[0]
    namespace = controller.enumerate_namespace()[0]
    controller.open()
    namespace.open()
    adm_common = fvt_adm(controller, namespace)
    
    size_list0 = ['0', '9', '10', '11', '12', '13', '14', '15', '16']
    size_list1 = ['1', '2', '3', '4', '5', '6', '7', '8']
        
    ret = adm_common.format(format_lbaf, ses=ses, project='vail', pi=pi)

    time.sleep(5)
    if ret == 0:
        ns_data = adm_common.ns_identify()
        if ns_data != -1:
            flbas = ns_data.flbas
            lba_ds = ns_data.lbaf(flbas & 0x0F).ds
            lba_size = 2 ** lba_ds	
            # logging.info("Identify LBA size is: {}".format(lba_size))
            
            lba_size_refer = 0
            
            if format_lbaf in size_list0:  # 512 byte LBA
                lba_size_refer = 512
            elif format_lbaf in size_list1:
                lba_size_refer = 4096

            if lba_size == lba_size_refer:
                logging.info("Format to {} LBA size successfully".format(lba_size))
            else:
                logging.error("Real lba size: {}, expected: {}".format(lba_size, lba_size_refer))
                pytest.fail("Real lba size: {}, expected: {}".format(lba_size, lba_size_refer))
            
            if str(flbas) == str(format_lbaf):
                logging.info("Format to flbas:{} successfully".format(flbas))
            else:
                logging.error("Real flbas: {}, expected: {}".format(flbas, format_lbaf))
                pytest.fail("Real flbas: {}, expected: {}".format(flbas, format_lbaf))
    else:
        logging.error("Format to LBAF {} failed".format(format_lbaf))
        pytest.fail("Format to LBAF {} failed".format(format_lbaf))

def get_pci_addr_list():
    '''
    Get pci addr of the nvme device
    '''
    cmd = "lspci -D | grep 'Non-Volatile memory' | grep 'Marvell' | grep -o '....:..:....'"
    _, pci_addr_list = execute_cmd(cmd, 10, out_flag = True)
    logging.info("PCI addr list: {}".format(pci_addr_list))
    return pci_addr_list

def enable_sriov(vf_amount, max_vf_amount):
    '''
    Enable SRIOV with #vf_amount VF, if vf_amount=0 means disable all VF
    Timeout to 10 seconds
    '''
    pci_addr_list = get_pci_addr_list()
    pci_addr = pci_addr_list[0] # there should be only one nvme ctrl during this test
    logging.info("Enable SRIOV with {} VFs".format(vf_amount))
    sriov_cmd = "echo {} > /sys/bus/pci/devices/{}/sriov_numvfs".format(vf_amount, pci_addr)
    if vf_amount > max_vf_amount:
        result = execute_cmd(sriov_cmd, 10, expect_fail = True, expect_err_info = "Numerical result out of range")
    else:
        result = execute_cmd(sriov_cmd, 10)

    logging.info("Result of enable sriov: {}".format(result))
    if result == 0:
        real_amount = len(get_pci_addr_list())
        result = 0
        if real_amount == 0:
            logging.error("No controllers found")
            result = -1
        elif real_amount != (vf_amount + 1):
            if vf_amount > max_vf_amount: 
                if real_amount == 1:
                    logging.info("Got 1 controller which is as expected")
                    result = 0
                else:
                    logging.warning("There might be controllers enabled before, just warning")
            else:
                logging.error("Found {} controllers, expected: {}".format(real_amount, vf_amount + 1))
                result = real_amount
        else:
            if vf_amount > max_vf_amount: 
                logging.error("vf amount exceed max.")
            else:
                logging.info("Expected {} controllers found".format(real_amount))

    return result

# Functions below are NS relevant
def ns_create(ctrl, ns_size, ns_cap, flb_setting=1, dps=0, nmic=0):
	'''
	Create ns, Note that create-ns does not attach the namespace to a controller, attach-ns does this.
	So ctrl in cmd is just there but no effect.
	'''
	logging.debug("Create ns - size: {}, capacity: {}, flb: {}, dps:{}, shared: {}".format(ns_size, ns_cap, flb_setting, dps, nmic))
	create_cmd = "nvme create-ns {} -s {} -c {} -f {} -m {} -d {}".format(ctrl, ns_size, ns_cap, flb_setting, nmic, dps)
	return execute_cmd(create_cmd, 30)

def ns_attach(ns_id, ctrl_list):
	'''
	Attach ns on controllers
	return 0 on success, others on fail
	'''
	ctrl_list = [str(i) for i in ctrl_list]
	ctrl_list_str = ",".join(ctrl_list)
	logging.debug("Attach ns(id:{}) to ctrl ({})".format(ns_id, ctrl_list_str))
	# it doesnot matter for the /dev/nvme param, just choose the first from ctrl_list
	attach_cmd = "nvme attach-ns /dev/nvme{} -n {} -c {}".format(ctrl_list[0], ns_id, ctrl_list_str) 
	return execute_cmd(attach_cmd, 30)

def ns_detach(ns_id, ctrl_list, expect_fail = False):
	'''
	Detach ns from controllers
	return 0 on success, others on fail
	'''
	ctrl_list = [str(i) for i in ctrl_list]
	ctrl_list_str = ",".join(ctrl_list)
	logging.debug("Detach ns(id:{}) from ctrl ({})".format(ns_id, ctrl_list_str))
	# it doesnot matter for the /dev/nvme param, just choose the first from ctrl_list
	detach_cmd = "nvme detach-ns /dev/nvme{} -n {} -c {}".format(ctrl_list[0], ns_id, ctrl_list_str)
	return execute_cmd(detach_cmd, 30, expect_fail = expect_fail)

def rescan_ctrl(ctrl_list):
	'''
	Rescan all controllers in ctrl_list(ctrl id list)
	return 0 on success, others on fail, but don't treat as fail criteria currently
	'''
	ret = 0
	for ctrl in ctrl_list:
		logging.debug("Rescan ctrl(id:{})".format(ctrl))
		rescan_cmd = "nvme ns-rescan /dev/nvme{}".format(ctrl)
		ret_temp = execute_cmd(rescan_cmd, 30)
		ret += ret_temp
	return ret

def ns_delete(ctrl, ns_id, expect_fail = False):
	'''
	Delelte NS, ctrl in cmd is just there but no effect.
	return 0 on success, others on fail
	'''
	logging.debug("Delete ns(id:{})".format(ns_id))
	delete_cmd = "nvme delete-ns {} -n {}".format(ctrl, ns_id)
	return execute_cmd(delete_cmd, 30, expect_fail = expect_fail)

def format_ns(ns, ns_id, lbaf=1, erase=0):
    '''
    For multi-ns scenariothat not yet tried with sherlock
    ns: NS name, it seems that NS string matters for format command
    format NS to specified LBAF
    return 0 on success, others on fail
    '''
    logging.info("Format NS to LBAF: {}".format(lbaf))
    format_cmd = "nvme format {} -n {} -l {} -s {} -p 0 -i 0".format(ns, ns_id, lbaf, erase) 
    return execute_cmd(format_cmd, 60)

def basic_multi_ns_setup(func_amount):
    '''
    Prepare NS setup for multi-pf/SRIOV, i.e. one NS on one function
    '''
    tests = ns_mgmt_cases(func_amount)
    attached_ns_list = []
    index = 1     
    ctrl_list = []
    for i in range(0, func_amount):
        ctrl_list.append(i)
    logging.info("Create NS for test")  
    for test in tests:
        logging.debug("Create NS - index: {} (start from 1)".format(index))
        controller = test['controller']
        size = test['size']
        capacity = test['capacity']
        flba = test['flba']
        dps = test['dps']
        shared = test['shared']
        if ns_create(controller, size, capacity, flba, dps, shared) != 0:
             pytest.fail("Create NS failed")
        index += 1
    
    logging.info("Attach NS for test")
    for i in range(0, func_amount):
        if ns_attach((i+1), [i]) != 0:
            pytest.fail("Attach NS failed")
        # As aligned, the number at the end is increased as attached order.
        attached_ns_list.append("/dev/nvme0n{}".format(i+1))  # the number after nvme is not fixed. Might be nvme0n, might be nvme15n, or some else
 
    logging.info("Attached NS list: {}".format(attached_ns_list))

    logging.info("Rescan all controllers")
    rescan_ctrl(ctrl_list) # rescan each controller
    ns_list_real = check_get_real_ns()
    if len(attached_ns_list) != len(ns_list_real):
        pytest.fail("Not all expected NS found, please check")
    return ns_list_real

def ns_mgmt_cases(ns_amount, shared_flag = 0, flbaf_list = [1]):
    '''
    flbaf_list: default is 1, if set to a list, then each config with a flbaf.
    '''
    tests = []

    total_capacity = int(get_specified_id_value("/dev/nvme0", "tnvmcap"))
    unalloc_capacity = int(get_specified_id_value("/dev/nvme0", "unvmcap"))

    if total_capacity == -1 or unalloc_capacity == -1:  # in this case, all capacity are not allocated
        logging.error("Please check if NS capacity correct")
        pytest.fail("Please check if NS capacity correct")
    else:
        capacity = hex(int(unalloc_capacity / ns_amount / 4096))  # unit for nvme cli is LBA

    for i in range(0, ns_amount):
        if i < len(flbaf_list):
            flba = flbaf_list[i]
        elif i >= len(flbaf_list): # Ramdomly allocate an LBAF for NS that not allocated yet in list
            flba = flbaf_list[random.randint(0, len(flbaf_list) - 1)]
        tests.append({'controller': '/dev/nvme0', 'size': capacity, 'capacity': capacity, 'flba': flba, 'dps': 0, 'shared': shared_flag})

    return tests

# Functions above are NS relevant

def get_specified_id_value(device, item):
    '''
    For multi-ns scenariothat not yet tried with sherlock
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
            logging.debug("Real value of {} is {}".format(item, real_value))
            return real_value
    else:
        logging.warning("No item {} found".format(item))
        return -1

def remove_device(pci_addr):
    '''
    Remove PCI device
    pci_addr: 0000:03:00.0
    '''
    logging.info("Remove PCIe device: {}".format(pci_addr))
    grant_mode = "sudo chmod 777 /sys/bus/pci/devices/" + pci_addr + "/remove"
    remove_pci_device = "sudo echo 1 >/sys/bus/pci/devices/" + pci_addr + "/remove"
    
    execute_cmd(grant_mode)
    ret = execute_cmd(remove_pci_device, 30)
    if ret != 0:
        logging.error("Remove device failed")
        pytest.fail("Remove device failed")

def rescan_device():
    '''
    Issue PCI rescan to rescan nvme drive. 
    controller reset issued during rescan
    '''
    logging.info("Rescan to detect PCIe device")
    grant_mode = "sudo chmod 777 /sys/bus/pci/rescan"
    rescan_cmd = "sudo echo 1 >/sys/bus/pci/rescan"
    execute_cmd(grant_mode)
    ret = execute_cmd(rescan_cmd, 30)
    if ret != 0:
        logging.error("Rescan device failed")
        pytest.fail("Rescan device failed")

def check_get_real_ns():
	'''
	check if NS really detected after attach and get the real NS name if detected
	Issue: The ctrl id and the real number in controllers might not be the same
	(for ex, id is 21, the controller might show as /dev/nvme20, doubtful, need to check with a third party drive)
	Return: all detected NS list
	'''
	ns_list = []
	list_cmd = "nvme list | grep nvme"
	ret, out = execute_cmd(list_cmd, 120, out_flag = True)
	# out ex: ['/dev/nvme0n1     S41FNX0M117868       SAMSUNG MZVLB256HAHQ-000L2               1         256.06  GB / 256.06  GB    512   B +  0 B   0L1QEXD7']
	if out == []:
		logging.warning("No NS found")
	else:
		for item in out:
			ns = item.split(" ")[0].strip()
			ns_list.append(ns)
	logging.info("Detected NS list: {}".format(ns_list))

	return ns_list

def parse_config(cfg_file, section, item):
    '''
    Parse configuration from specified cfg file
    @return: value or value list
    '''
    config = ConfigParser()
    config.read(cfg_file)

    item_value = config.get(section, item).strip()
    if "," in item_value:
        item_value = item_value.split(",")
    
    return item_value
#!/usr/bin/python
######################################################################################################################
# Copyright (c) 2022 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2022 Marvell Semiconductor.
#
# Version Control Information:
#
#  $Id$
#  revision: 0.1
#
#  Author:  Leon Cheng
#
#  May. 20, 2022
#
#####################################################################################################################

import logging
import pytest
from common import util
import re
from common import fvt_adm_cmd_common
import os
import threading

lba_size = 4096 # default is 4k 

def report_zones(ns = "/dev/nvme0n1", zone_amount = 4, check_list = []):
    '''
    list all zones information
    zone_amount: how many zones in the NS
    check_list: info to be checked, for ex. 
    [{"SLBA": 0, "WP": 0, "Cap": 0, "State": 0x10, "Type": 0x2}, {}, {"SLBA": 0, "WP": 0x2000}, {}]
    Will check five items for the first zone, and two items for the third zone, no need check for others    
    out example:
    ['nr_zones: 4', 
    'SLBA: 0          WP: 0          Cap: 0x2000     State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   ', 
    'SLBA: 0x2000     WP: 0x2000     Cap: 0x2000     State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   ', 
    'SLBA: 0x4000     WP: 0x4000     Cap: 0x2000     State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   ', 
    'SLBA: 0x6000     WP: 0x6000     Cap: 0x2000     State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   ']
    '''
    report_cmd = "sudo nvme zns report-zones {}".format(ns)
    ret, out = util.execute_cmd(report_cmd, timeout=30, out_flag=True)
    if ret != 0:
        logging.error("Get zone list failed")
        pytest.fail("Get zone list failed")
        
    if int(out[0].split(":")[1].strip()) != zone_amount or len(out) != (zone_amount + 1):
        logging.error("Zones amount mismatched, expected: {}".format(zone_amount))
        pytest.fail("Zones amount mismatched, expected: {}".format(zone_amount))

    logging.debug("Check list: {}".format(check_list))
    actual_info = out[1:]
    real_status = []
    pattern = "SLBA:(.+)WP:(.+)Cap:(.+)State:(.+)Type:(.+)Attrs:(.+)AttrsInfo:(.+)"
    # parse all zone info to a list
    for i in range(0, zone_amount):
        temp = re.search(pattern, actual_info[i])
        slba = temp.group(1).strip()
        wp = temp.group(2).strip()
        cap = temp.group(3).strip()
        state = temp.group(4).strip()
        type = temp.group(5).strip()
        real_status.append({"SLBA": slba, "WP": wp, "Cap": cap, "State": state, "Type": type})
    for check_items in check_list:
        if len(check_items) != 0:
            logging.info("Checking status for SLBA:{}".format(real_status[check_list.index(check_items)]["SLBA"]))
            index = check_list.index(check_items)
            slba = real_status[index]["SLBA"]
            wp = real_status[index]["WP"]
            cap = real_status[index]["Cap"]
            state = real_status[index]["State"]
            type = real_status[index]["Type"]
            for key, value in check_items.items():
                if value == "0x0":
                    value = "0" # in output, 0 is shown as 0 not 0x0
                if key.lower() == "slba":
                    if value != slba:
                        logging.error("SLBA check failed, real: {}, expected: {}".format(slba, value))
                        logging.info("Current status: {}".format(real_status[check_list.index(check_items)]))
                        pytest.fail("SLBA check failed, real: {}, expected: {}".format(slba, value))
                    logging.debug("SLBA check passed")
                elif key.lower() == "wp":
                    if value != wp:
                        logging.error("WP check failed, real: {}, expected: {}".format(wp, value))
                        logging.info("Current status: {}".format(real_status[check_list.index(check_items)]))
                        pytest.fail("WP check failed, real: {}, expected: {}".format(wp, value))
                    logging.debug("WP check passed")
                elif key.lower() == "cap":
                    if value != cap:
                        logging.error("CAP check failed, real: {}, expected: {}".format(cap, value))
                        logging.info("Current status: {}".format(real_status[check_list.index(check_items)]))
                        pytest.fail("CAP check failed, real: {}, expected: {}".format(cap, value))
                    logging.debug("CAP check passed")
                elif key.lower() == "state":
                    if value != state:
                        logging.error("State check failed, real: {}, expected: {}".format(state, value))
                        logging.info("Current status: {}".format(real_status[check_list.index(check_items)]))
                        pytest.fail("State check failed, real: {}, expected: {}".format(state, value))
                    logging.debug("State check passed")
                elif key.lower() == "type":
                    if value != type:
                        logging.error("Type check failed, real: {}, expected: {}".format(type, value))
                        logging.info("Current status: {}".format(real_status[check_list.index(check_items)]))
                        pytest.fail("Type check failed, real: {}, expected: {}".format(type, value))
                    logging.debug("Type check passed")
    logging.info("All zones info check passed")
    return real_status
                        
def zns_id_ns(ctrl, ns, ns_str = "/dev/nvme0n1", zone_amount = 4):
    '''
    ZNS namespace identify
    return block amount of each zone in int.
    '''
    identify_cmd = "sudo nvme zns id-ns {}".format(ns_str)
    ret, out = util.execute_cmd(identify_cmd, out_flag=True)
    if ret != 0:
        logging.error("ZNS identify NS failed")
        pytest.fail("ZNS identify NS failed")
    
    # items to be checked
    zoc = "0"  # refer to spec: the capacity for a zone may change without a change to the format of the zoned namespace
    ozcs = "1" # refer to spec: any User Data Read Access Command is allowed to perform read operations that specify an LBA range containing logical blocks in more than one zone
    mar = "0xffffffff" # Maximum Active Resources
    mor = "0xffffffff" # Maximum Open Resources
    lbaf = "1" # default lbaf is 1
    total_block = None
    for item in out:
        if "zoc" in item:
            zoc_v = item.split(":")[1].strip()
            if zoc_v != zoc:
                logging.error("ZOC value check failed, real: {}, expected: {}".format(zoc_v, zoc))
                pytest.fail("ZOC value check failed, real: {}, expected: {}".format(zoc_v, zoc))
            logging.info("Check ZOC passed")
        if "ozcs" in item:
            ozcs_v = item.split(":")[1].strip()
            if ozcs_v != ozcs:
                logging.error("OZCS value check failed, real: {}, expected: {}".format(ozcs_v, ozcs))
                pytest.fail("OZCS value check failed, real: {}, expected: {}".format(ozcs_v, ozcs))
            logging.info("Check OZCS passed")
        if "mar" in item:
            mar_v = item.split(":")[1].strip()
            if mar_v != mar:
                logging.error("MAR value check failed, real: {}, expected: {}".format(mar_v, mar))
                pytest.fail("MAR value check failed, real: {}, expected: {}".format(mar_v, mar))
            logging.info("Check MAR passed")
        if "mor" in item:
            mor_v = item.split(":")[1].strip()
            if mor_v != mor:
                logging.error("MOR value check failed, real: {}, expected: {}".format(mor_v, mor))
                pytest.fail("MOR value check failed, real: {}, expected: {}".format(mor_v, mor))
            logging.info("Check MOR passed")
        if "in use" in item:
            # lbafe  1: zsze:0x2000 zdes:0 (in use)
            v_list = item.split(":")
            lbaf_v = v_list[0].strip("lbafe").strip()
            if lbaf_v != lbaf:
                logging.error("LBAF value check failed, real: {}, expected: {}".format(lbaf_v, lbaf))
                pytest.fail("LBAF value check failed, real: {}, expected: {}".format(lbaf_v, lbaf))
            total_block_each_zone = v_list[2].strip("zdes").strip()
            total_block = fvt_adm_cmd_common.fvt_adm(ctrl, ns).ns_identify().nsze            
            #zone capacity should be 2^n
            block_zone_tmp = total_block // zone_amount
            total_block_each_zone_expected = hex(2 ** (len(bin(block_zone_tmp)) - 3))        
            if total_block_each_zone != total_block_each_zone_expected:
                logging.error("Logical block of each zone is unexpected, total: {}, each: {}".format(total_block, total_block_each_zone))
                pytest.fail("Logical block of each zone is unexpected, total: {}, each: {}".format(total_block, total_block_each_zone))
            logging.info("Total logical block amount of each zone is:{}".format(total_block_each_zone))
    logging.info("ZNS id ns check passed")
    return int(total_block_each_zone, 16)

def zns_id_ctrl(ctrl = "/dev/nvme0"):
    '''
    ZNS controller identify
    '''
    identify_cmd = "sudo nvme zns id-ctrl {}".format(ctrl)
    ret, out = util.execute_cmd(identify_cmd, out_flag=True)
    if ret != 0:
        logging.error("ZNS identify ctrl failed")
        pytest.fail("ZNS identify ctrl failed")
    
    for item in out:
        if "zasl" in item:
            zasl_v = item.split(":")[1].strip()
            if zasl_v != "0":  #a value of 0h in this field indicates that the maximum data transfer size for the Zone Append command is indicated by the Maximum Data Transfer Size (MDTS) field
                logging.error("The value of ZASL should be 0")
                pytest.fail("The value of ZASL should be 0")

def fio_runner(ns, io_type, size, bs, offset, q_depth, log_folder, timeout, log_str, check_result = True):
    '''
    Run FIO, for easy call by multi-threading
    check_result: if check fio result after IO run
    '''
    util.fio_runner(ns_str=ns, io_type=io_type, size=size, bs=bs, offset=offset, q_depth=q_depth, time_based=0, log_folder=log_folder, timeout=timeout, log_str=log_str, check_result=check_result)
    
def run_io_on_zns(zone_amount, io_blocks, ns = "/dev/nvme0n1", log_folder = os.getcwd(), io_type = "read", bs="128k", qd = "1", timeout = 300):
    '''
    Run fio on all zones at the same time
    io_blocks: how many blocks to do IO on
    '''
    thread_list = []
    size_each = io_blocks * lba_size  # default LBAF is 1, lba size is 4096
    offset = 0
    for i in range(0, zone_amount):
        offset = size_each * i
        log_str = "zone_{}_{}.log".format(i, io_type)
        t = threading.Thread(target=fio_runner, args=(ns, io_type, size_each, bs, offset, qd, log_folder, timeout, log_str, False))
        t.start()
        thread_list.append(t)

    for t in thread_list:
        t.join(timeout = 300)

def reset_zone(check_list, SLBA = None, all = False, ns = "/dev/nvme0n1", expected_error = None):
    '''
    zns reset zone
    SLBA/all: exclusive argument, reset specified zone or reset all zones
    all: True or False
    expected_error: if expect fail, which error should be recorded, if reset all zones, always return success
    check_list: check status after reset, usually it's original status list
    '''
    if SLBA != None and all != False:
        logging.error("Exclusive argument, please correct")
        pytest.exit("Exclusive argument, please correct")
    elif SLBA == None and all == False:
        logging.error("Exclusive argument, you need to specify at least one")
        pytest.exit("Exclusive argument, you need to specify at least one")
    if all:
        logging.info("Reset all zones")
    else:
        logging.info("Reset zone with SLBA:{}".format(SLBA))
    ori_status = report_zones()
        
    index = 0
    check_list_real = []
    expect_fail = False
    if not all:
        reset_cmd = "sudo nvme zns reset-zone {} -s {}".format(ns, SLBA)
        for check_items in check_list:
            if check_items["SLBA"] == SLBA:
                index = check_list.index(check_items)
                break
        else:
            logging.error("SLBA is invalid")
            pytest.fail("SLBA is invalid")
        if expected_error == None:
            # expect success, status restored to default
            ori_status[index] = check_list[index]
            check_list_real = ori_status
        else:
            # expect failure, status not changed, for reset, only reset ZSRO/ZSO zone return error, but no way to realize ZSRO/ZSO state zone.
            check_list_real = ori_status
            expect_fail = True
    elif all:
        reset_cmd = "sudo nvme zns reset-zone {} -a 1".format(ns)
        if expected_error == None:
            for check_items in ori_status:
                if check_items["State"] in ["0x20", "0x30", "0x40", "0xe0"]: 
                    ori_status[ori_status.index(check_items)] = check_list[ori_status.index(check_items)]
            check_list_real = ori_status
        else:
            check_list_real = ori_status
    
    ret, out = util.execute_cmd(reset_cmd, out_flag=True, expect_fail=expect_fail)
    if ret != 0:
        logging.info("Reset zone cmd failed")
        pytest.fail("Reset zone cmd failed")
    
    report_zones(check_list = check_list_real)
    if not all:
        if expected_error != None:
            if expected_error not in out[0]:
                logging.error("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
                pytest.fail("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
            else:
                logging.info("Error status check passed")
    
    logging.info("Zone status after reset: {}".format(check_list_real))
                
def open_zone(SLBA = None, all = False, ns = "/dev/nvme0n1", expected_error = None):
    '''
    zns open zone
    SLBA/all: exclusive argument, open specified zone or open all zones
    all: True or False
    expected_error: if expect fail, which error should be recorded, if open all zones, always return success
    note: due to specification, there's difference if Select All to "1" or not, i.e. open one zone or all zone. 
    If Select All to '1', state transition from ZSE/ZSIO to ZSEO is excluded. 
    '''
    if SLBA != None and all != False:
        logging.error("Exclusive argument, please correct")
        pytest.exit("Exclusive argument, please correct")
    elif SLBA == None and all == False:
        logging.error("Exclusive argument, you need to specify at least one")
        pytest.exit("Exclusive argument, you need to specify at least one")
    
    if all:
        logging.info("Open all zones")
        if expected_error != None:
            logging.error("If open all zones, always return success for nvme cli, please correct")
            pytest.exit("If open all zones, always return success for nvme cli, please correct")
    else:
        logging.info("Open zone with SLBA:{}".format(SLBA))
    ori_status = report_zones()
    index = 0
    check_list_real = []

    expect_fail = False
    # check_list_ori = copy.deepcopy(check_list)  # copy to avoid list being changed by current function
    if not all:
        open_cmd = "sudo nvme zns open-zone {} -s {}".format(ns, SLBA)
        for check_items in ori_status:
            if check_items["SLBA"] == SLBA:
                index = ori_status.index(check_items)
                break
        else:
            logging.error("SLBA is invalid")
            pytest.fail("SLBA is invalid")
        if expected_error == None:
            # expect success, state changed to ZSEO(0x30)
            ori_status[index]["State"] = "0x30"
            check_list_real = ori_status
        else:
            # expect failure, status not changed
            check_list_real = ori_status
            expect_fail = True
    elif all: # For Select All to 1, nvme cli always return success. Reason: Imagin some success, some fail, how to report?
        open_cmd = "sudo nvme zns open-zone {} -a 1".format(ns)
        if expected_error == None:
            for check_items in ori_status:
                if check_items["State"] == "0x40": # only ZSC transit to ZSEO if select all to "1"
                    check_items["State"] = "0x30"
            check_list_real = ori_status
        
    ret, out = util.execute_cmd(open_cmd, out_flag=True, expect_fail=expect_fail)
    if ret != 0:
        logging.info("Open zone cmd failed")
        pytest.fail("Open zone cmd failed")
    
    report_zones(check_list = check_list_real)
    if not all:
        if expected_error != None:
            if expected_error not in out[0]:
                logging.error("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
                pytest.fail("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
            else:
                logging.info("Error status check passed")
    
    logging.info("Zone status after open: {}".format(check_list_real))
    
def close_zone(SLBA = None, all = False, ns = "/dev/nvme0n1", expected_error = None):
    '''
    zns close zone
    SLBA/all: exclusive argument, close specified zone or close all zones
    all: True or False
    expected_error: if expect fail, which error should be recorded, if close all zones, always return success
    '''
    if SLBA != None and all != False:
        logging.error("Exclusive argument, please correct")
        pytest.exit("Exclusive argument, please correct")
    elif SLBA == None and all == False:
        logging.error("Exclusive argument, you need to specify at least one")
        pytest.exit("Exclusive argument, you need to specify at least one")
    
    if all:
        logging.info("Close all zones")
    else:
        logging.info("Close zone with SLBA:{}".format(SLBA))
    ori_status = report_zones()
        
    index = 0
    check_list_real = []
    expect_fail = False
    # check_list_ori = copy.deepcopy(check_list)  # copy to avoid list being changed by current function
    if not all:
        close_cmd = "sudo nvme zns close-zone {} -s {}".format(ns, SLBA)
        for check_items in ori_status:
            if check_items["SLBA"] == SLBA:
                index = ori_status.index(check_items)
                break
        else:
            logging.error("SLBA is invalid")
            pytest.fail("SLBA is invalid")
        if expected_error == None:
            # expect success, state changed to ZSC(0x40)
            ori_status[index]["State"] = "0x40"
            check_list_real = ori_status
        else:
            # expect failure, status not changed
            check_list_real = ori_status
            expect_fail = True
    elif all:
        close_cmd = "sudo nvme zns close-zone {} -a 1".format(ns)
        if expected_error == None:
            for check_items in ori_status:
                if check_items["State"] in ["0x20", "0x30"]:
                    check_items["State"] = "0x40"
            check_list_real = ori_status
        else:
            check_list_real = ori_status
        
    ret, out = util.execute_cmd(close_cmd, out_flag=True, expect_fail=expect_fail)
    if ret != 0:
        logging.info("Close zone cmd failed")
        pytest.fail("Close zone cmd failed")
    
    report_zones(check_list = check_list_real)
    if not all:
        if expected_error != None:
            if expected_error not in out[0]:
                logging.error("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
                pytest.fail("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
            else:
                logging.info("Error status check passed")
    
    logging.info("Zone status after close: {}".format(check_list_real))
    
def finish_zone(SLBA = None, all = False, ns = "/dev/nvme0n1", expected_error = None):
    '''
    zns finish zone
    SLBA/all: exclusive argument, finish specified zone or finish all zones
    all: True or False
    expected_error: if expect fail, which error should be recorded, if finish all zones, always return success
    note: due to specification, there's difference if Select All to "1" or not, i.e. finish one zone or all zone. 
    If Select All to '1', state transition from ZSE to ZSF is excluded. 
    Note2: finish should not change CAP, CAP only be changed after format changed
    '''
    if SLBA != None and all != False:
        logging.error("Exclusive argument, please correct")
        pytest.exit("Exclusive argument, please correct")
    elif SLBA == None and all == False:
        logging.error("Exclusive argument, you need to specify at least one")
        pytest.exit("Exclusive argument, you need to specify at least one")
    
    if all:
        logging.info("Finish all zones")
    else:
        logging.info("Finish zone with SLBA:{}".format(SLBA))
    ori_status = report_zones()
        
    index = 0
    check_list_real = []
    expect_fail = False
    # check_list_ori = copy.deepcopy(check_list)  # copy to avoid list being changed by current function
    if not all:
        finish_cmd = "sudo nvme zns finish-zone {} -s {}".format(ns, SLBA)
        for check_items in ori_status:
            if check_items["SLBA"] == SLBA:
                index = ori_status.index(check_items)
                break
        else:
            logging.error("SLBA is invalid")
            pytest.fail("SLBA is invalid")
        if expected_error == None:
            # expect success, state changed to ZSF(0xe0)
            ori_status[index]["State"] = "0xe0"
            # ori_status[index]["WP"] = hex(int(ori_status[index]["WP"], 16) + int(ori_status[index]["Cap"], 16))
            # ori_status[index]["Cap"] = "0"
            check_list_real = ori_status
        else:
            # expect failure, status not changed
            check_list_real = ori_status
            expect_fail = True
    elif all:
        finish_cmd = "sudo nvme zns finish-zone {} -a 1".format(ns)
        if expected_error == None:
            for check_items in ori_status:
                if check_items["State"] in ["0x20", "0x30", "0x40"]:
                    check_items["State"] = "0xe0"  # ZSF
                    # check_items["WP"] = hex(int(check_items["Cap"], 16) + int(check_items["WP"], 16))
                    # check_items["Cap"] = "0"                    
            check_list_real = ori_status
        else:
            check_list_real = ori_status
        
    ret, out = util.execute_cmd(finish_cmd, out_flag=True, expect_fail=expect_fail)
    if ret != 0:
        logging.info("Finish zone cmd failed")
        pytest.fail("Finish zone cmd failed")
        
    report_zones(check_list = check_list_real)
    if not all:
        if expected_error != None:
            if expected_error not in out[0]:
                logging.error("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
                pytest.fail("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
            else:
                logging.info("Error status check passed")
    
    logging.info("Zone status after finish: {}".format(check_list_real))
    
def offline_zone(SLBA = None, all = False, ns = "/dev/nvme0n1", expected_error = None):
    '''
    zns offline zone
    SLBA/all: exclusive argument, offline specified zone or offline all zones
    all: True or False
    expected_error: if expect fail, which error should be recorded, if offline all zones, always return success
    actually only ZSRO zone can be offline, no way to switch into ZSRO
    '''
    if SLBA != None and all != False:
        logging.error("Exclusive argument, please correct")
        pytest.exit("Exclusive argument, please correct")
    elif SLBA == None and all == False:
        logging.error("Exclusive argument, you need to specify at least one")
        pytest.exit("Exclusive argument, you need to specify at least one")
    
    if all:
        logging.info("Offline all zones")
    else:
        logging.info("Offline zone with SLBA:{}".format(SLBA))
    ori_status = report_zones()
        
    index = 0
    check_list_real = []
    expect_fail = False
    # check_list_ori = copy.deepcopy(check_list)  # copy to avoid list being changed by current function
    if not all:
        offline_cmd = "sudo nvme zns offline-zone {} -s {}".format(ns, SLBA)
        for check_items in ori_status:
            if check_items["SLBA"] == SLBA:
                index = ori_status.index(check_items)
                break
        else:
            logging.error("SLBA is invalid")
            pytest.fail("SLBA is invalid")
        if expected_error == None:
            # expect success, state changed to ZSO(0x40)
            ori_status[index]["State"] = "0xf0"
            check_list_real = ori_status
        else:
            # expect failure, status not changed
            check_list_real = ori_status
            expect_fail = True
    elif all:
        offline_cmd = "sudo nvme zns offline-zone {} -a 1".format(ns)
        if expected_error == None:
            for check_items in ori_status:
                if check_items["State"] in ["0xd0"]:
                    check_items["State"] = "0xf0"  # ZSO
            check_list_real = ori_status
        else:
            check_list_real = ori_status
        
    ret, out = util.execute_cmd(offline_cmd, out_flag=True, expect_fail=expect_fail)
    
    if ret != 0:
        logging.info("Offline zone cmd failed")
        pytest.fail("Offline zone cmd failed")
    
    report_zones(check_list = check_list_real)
    if not all:
        if expected_error != None:
            if expected_error not in out[0]:
                logging.error("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
                pytest.fail("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
            else:
                logging.info("Error status check passed")
    
    logging.info("Zone status after offline: {}".format(check_list_real))
    
def append_zone(size_to_append, SLBA, ns = "/dev/nvme0n1", check_after = False, expected_error = None):
    '''
    ZNS append command
    size_to_append: size of data in block(hex value), it can be a total value to be append, if it's too big, we will split it to multiple append cmd
    check_after: if check zone status after append
    expected_error: if expect fail, which error should be recorded
    '''
    ori_status = []
    index = 0
    check_status = []
    logging.info("Append zone with SLBA:{} for {} blocks".format(SLBA, size_to_append))
    large_ref = 262144 # 256k
    
    size_int_byte = int(size_to_append, 16) * lba_size
    if check_after:  # If need to check after append
        if size_int_byte > large_ref: # we do not do check if append size larger than 256k
            logging.error("SLBA is invalid")
            pytest.fail("SLBA is invalid")
            
        ori_status = report_zones()

        for check_items in ori_status:
            if check_items["SLBA"] == SLBA:
                index = ori_status.index(check_items)
                break
        else:
            logging.error("No matched SLBA found")
            pytest.fail("No matched SLBA found")
            
        if ori_status[index]["State"] != "0x30" and expected_error == None:  # ZSEO do not transmit to ZSIO
            check_status = ori_status
            check_status[index]["State"] = "0x20"
            tmp_wp = hex(int(ori_status[index]["WP"], 16) + int(size_to_append, 16))
            #### Cap should not be changed by append
            # tmp_cap = hex(int(ori_status[index]["Cap"], 16) - int(size_to_append, 16))
            check_status[index]["WP"] = tmp_wp
            # check_status[index]["Cap"] = tmp_cap
            
    expect_fail = False
    if expected_error != None:
        expect_fail = True    

    # For large amount of data to write, split to multiple append command
    if size_int_byte > large_ref:
        times = size_int_byte // large_ref
        size_to_append = 0x40000
        eliminate_log = True
    else:
        times = 1
        eliminate_log = False
        size_to_append = hex(size_int_byte)
        
    for i in range(0, times):
        # an enter is required for zone-append command to output result, thus echo -e "\n" is used
        append_cmd = 'echo -e "\\n" | sudo nvme zns zone-append {} -s {} -z {}'.format(ns, SLBA, size_to_append)
        ret, out = util.execute_cmd(append_cmd, out_flag=True, expect_fail=expect_fail, eliminate_log=eliminate_log)
        if ret != 0:
            logging.info("Append zone cmd failed")
            pytest.fail("Append zone cmd failed")
    
    if expected_error != None:
        if expected_error not in out[0]:
            logging.error("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
            pytest.fail("Expected error mismatch, expect: {}, real: {}".format(expected_error, out[0]))
        else:
            logging.info("Error status check passed")
    
    logging.info("Zone status after append: {}".format(report_zones(check_list = check_status)))  # if check_after, will check referring to check_status, otherwise, check_list is empty, i.e. no check
        
    logging.info("Append zone passed")
    
def nvme_write(SLBA, blocks, data_size_in_bytes, ns = "/dev/nvme0n1", expected_error = None):
    '''
    nvme write cmd
    SLBA/blocks/data_size_in_bytes, refer to nvme-cli
    note: blocks in nvme-cli is 0 based, but here adjust to 1 based
    '''
    logging.info("Send write command")
    write_cmd = "echo -e '\\n' | sudo nvme write {} -s {} -c {} -z {}".format(ns, SLBA, int(blocks - 1), data_size_in_bytes)
    
    expect_fail = False
    if expected_error != None:
        expect_fail = True
        logging.info("Expected error: {}".format(expected_error))
    
    ret = util.execute_cmd(write_cmd, expect_fail=expect_fail, expect_err_info=expected_error)
    
    if ret != 0:
        logging.error("Write failed or no expected error met: {}".format(expected_error))
        pytest.fail("Write failed or no expected error met: {}".format(expected_error))
    
    
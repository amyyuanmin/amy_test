#!/usr/bin/python
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
#Test Category Name : ZNS test
#Test Category Description : ZNS test for Vail SDK
#Test Steps:

#####################################################################################################################

# ZNS is supported from nvme-cli 1.13

import pytest
import logging
import os, shutil
from common import fvt_adm_cmd_common
from common import util
from . import zns_util
import copy

class Test_ZNS:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global zns_result
        folder_name = hostname + "_zns_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        zns_result = log_folder + '/zns_result.log'

        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.fixture(scope="function", autouse=True)
    def function_teardown(self, request):
        global test_result
        test_result = "Fail"
        yield
        with open(zns_result, "a+") as f:
            f.write('%-25s:%-35s\n' % (request.node.name.replace("test_", ""), test_result))
        logging.info("Reset all zones to restore test env.")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        
    @pytest.mark.timeout(timeout=300, method="signal")
    def test_zns_identify(self, zone_amount, controller, namespace):
        '''
        ZNS identify check
        This test cannot be skipped since the total_block_each_zone is used by other functions
        '''
        # total_block_each_zone: int
        global total_block_each_zone, initial_zones, test_result, lba_size
        logging.info("##########Start test of ZNS Identify##########")
        total_block_each_zone = zns_util.zns_id_ns(ctrl=controller, ns=namespace, zone_amount=int(zone_amount))
        zns_util.zns_id_ctrl()
        lba_size = 4096  # default for Vail SDK
        
        initial_zones = []  # initial zone status info
        for i in range(0, int(zone_amount)):
            slba = total_block_each_zone * i
            wp = slba
            config = {"SLBA": hex(slba) if slba !=0 else "0", "WP": hex(wp) if wp !=0 else "0", "Cap": hex(total_block_each_zone), "State": "0x10", "Type": "0x2"}
            initial_zones.append(config)
        
        test_result = "Pass"
    
    @pytest.mark.timeout(timeout=300, method="signal")
    def test_zns_receive_command(self, zone_amount):
        '''
        ZNS Management receive command, check some key items: SLBA, WP, Cap, State, Type(all are 0x2, i.e. Sequential Write Required supported)
        '''
        global test_result         
        logging.info("##########Start test of ZNS Management Receive Command check##########")
        logging.info("Check initial configuration")
        zns_util.report_zones(zone_amount=int(zone_amount), check_list=initial_zones)
        test_result = "Pass"
    
    @pytest.mark.timeout(timeout=1800, method="signal")
    def test_zns_basic_io(self, zone_amount, controller, namespace, build):
        '''
        Basic IO check on ZNS
        1. FIO sequential write to ZNS within the ZNS range.
        2. FIO read to verify.
        '''
        global test_result
        fio_log_folder = "zns_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)  

        logging.info("##########Start test of ZNS Basic IO##########")
        logging.info("Run sequential write on all zones")
        zns_util.run_io_on_zns(zone_amount=int(zone_amount), io_blocks=total_block_each_zone, io_type="write", log_folder=fio_log_folder)
        util.check_fio_logs(fio_log_folder=fio_log_folder)
        logging.info("Check status of each zone")
        check_list = []
        for i in range(0, int(zone_amount)):
            # ####to be recovered, Cap should not be changed by write, but currently it's changed
            # config = {"State": "0xe0", "Cap": initial_zones[0]['Cap']}  # Cap should not be changed by write 
            config = {"State": "0xe0"}
            check_list.append(config)
        zns_util.report_zones(zone_amount=int(zone_amount), check_list=check_list)
        
        logging.info("Read out data for verification")
        zns_util.run_io_on_zns(zone_amount=int(zone_amount), io_blocks=total_block_each_zone, io_type="read", log_folder=fio_log_folder)
        util.check_fio_logs(fio_log_folder=fio_log_folder, except_key="write")
        
        if build == "E2e":
            logging.info("Env cleanup: format the NS")
            fvt_adm_cmd_common.fvt_adm(controller, namespace).format(format_lbaf="1")
        
        test_result = "Pass"
    
    @pytest.mark.timeout(timeout=1800, method="signal")
    def test_zns_send_command(self, controller, namespace, build):
        '''
        ZNS management send command
        Covering all state transition including error scenarios
        Set Zone Descriptor Extension - ZSE->ZSC - Not support
        Reset : ZSEO -> ZSE, ZSIO->ZSE,ZSC->ZSE, ZSF->ZSE, ZSE->ZSE, others(ZSO/ZSRO): Invalid Zone State Transition
        Open: ZSE->ZSEO, ZSIO->ZSEO(not if -a 1, refer below), ZSC->ZSEO, ZSEO->ZSEO, others: Invalid Zone State Transition.
        Finish: ZSE->ZSF(not if -a 1, refer below), ZSIO->ZSF, ZSEO->ZSF, ZSC->ZSF, ZSF->ZSF, others(ZSO/ZSRO): Invalid Zone State Transition.
        Close: ZSIO->ZSC, ZSEO->ZSC, ZSC->ZSC, others: Invalid Zone State Transition.
        Offline: ZSRO->ZSO, ZSO->ZSO, others: Invalid Zone State Transition
        Write: ZSC->ZSIO, ZSE->ZSIO
        '''
        global test_result
        fio_log_folder = "zns_send_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)  
        logging.info("####Zone management send to each zone####")
        tmp_status = copy.deepcopy(initial_zones)  # to avoid data change of initial_zones in scripts
        for zone in tmp_status:
            current_status = zns_util.report_zones()
            logging.info("####Zone SLBA: {}####".format(zone['SLBA']))
            logging.info("ZSE -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"])
            logging.info("ZSC -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"])
            logging.info("ZSC -> ZSF")
            zns_util.finish_zone(SLBA=zone["SLBA"])
            logging.info("ZSF -> ZSF")
            zns_util.finish_zone(SLBA=zone["SLBA"])
            logging.info("Invalid transfer for zone open: ZSF -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"], expected_error="INVALID_ZONE_STATE_TRANSITION")
            logging.info("Invalid transfer for zone close: ZSF -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"], expected_error="INVALID_ZONE_STATE_TRANSITION")
            logging.info("ZSF -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("ZSE -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("ZSE -> ZSF")
            zns_util.finish_zone(SLBA=zone["SLBA"])
            logging.info("ZSF -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("Invalid transfer for zone close: ZSE -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"], expected_error="INVALID_ZONE_STATE_TRANSITION")
            logging.info("ZSE -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSF")
            zns_util.finish_zone(SLBA=zone["SLBA"])
            logging.info("ZSF -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("ZSE -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"])
            logging.info("ZSC -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("ZSE -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"])
            logging.info("ZSC -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            tmp_status_internal = copy.deepcopy(current_status)  # refresh data
            logging.info("ZSE -> ZSIO")
            # default lba size is 4096(4k)
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zse_zsio_log.log")
            tmp_status_internal[tmp_status.index(zone)]["State"] = "0x20"  # ZSIO
            tmp_status_internal[tmp_status.index(zone)]["WP"] = hex(int(zone["SLBA"], 16) + 256)  # 1m = 256 * 4k            
            #need to be changed since Cap should not be changed by write - changed
            tmp_status_internal[tmp_status.index(zone)]["Cap"] = zone["Cap"]  # 1m = 256 * 4k
            zns_util.report_zones(check_list=tmp_status_internal)
            logging.info("ZSIO -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("ZSE -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            logging.info("ZSEO -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"])
            
            tmp_status_internal = copy.deepcopy(current_status)  # refresh data
            logging.info("ZSC -> ZSIO")
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zsc_zsio_log.log")
            tmp_status_internal[tmp_status.index(zone)]["State"] = "0x20"  # ZSIO
            tmp_status_internal[tmp_status.index(zone)]["WP"] = hex(int(zone["SLBA"], 16) + 256) # 1M
            #need to be changed since Cap should not be changed by write - changed
            tmp_status_internal[tmp_status.index(zone)]["Cap"] = zone["Cap"]  # 1m = 256 * 4k
            zns_util.report_zones(check_list=tmp_status_internal)
            logging.info("ZSIO -> ZSC")
            zns_util.close_zone(SLBA=zone["SLBA"])
            
            logging.info("ZSC -> ZSIO")
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size + 1048576), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zsc_zsio_log_2.log")
            logging.info("ZSIO -> ZSF")
            zns_util.finish_zone(SLBA=zone["SLBA"])
            
            logging.info("ZSF -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
            logging.info("ZSE -> ZSIO")
            # default lba size is 4096(4k)
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zse_zsio_log_2.log")
            logging.info("ZSIO -> ZSEO")
            zns_util.open_zone(SLBA=zone["SLBA"])
            tmp_status_internal = copy.deepcopy(current_status)  # refresh data
            logging.info("Invalid transfer: ZSEO -> ZSIO")
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size + 1048576), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zsc_zsio_log_2.log")
            #need to be changed, ZSEO cannot be transited to ZSIO by write - changed
            tmp_status_internal[tmp_status.index(zone)]["State"] = "0x30"  # ZSEO
            tmp_status_internal[tmp_status.index(zone)]["WP"] = hex(int(zone["SLBA"], 16) + 512) # 2M
            #need to be changed since Cap should not be changed by write - changed
            tmp_status_internal[tmp_status.index(zone)]["Cap"] = zone["Cap"]  # 1m = 256 * 4k
            zns_util.report_zones(check_list=tmp_status_internal)
            logging.info("ZSEO -> ZSE")
            zns_util.reset_zone(check_list=initial_zones, SLBA=zone["SLBA"])
        logging.info("####Zone management send to all zones####")
        logging.info("Invalid transfer from zone open(-a 1): ZSE -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSE -> ZSEO one by one")
        for zone in initial_zones:
            zns_util.open_zone(SLBA=zone["SLBA"])
        logging.info("ZSEO -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSEO -> ZSC")
        zns_util.close_zone(all=True)
        logging.info("ZSC -> ZSC")
        zns_util.close_zone(all=True)
        logging.info("ZSC -> ZSF")
        zns_util.finish_zone(all=True)
        logging.info("ZSF -> ZSF")
        zns_util.finish_zone(all=True)
        logging.info("Invalid transfer for zone open: ZSF -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("Invalid transfer for zone close: ZSF -> ZSC")
        zns_util.close_zone(all=True)
        logging.info("ZSF -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("ZSE -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("Invalid transfer from zone finish(-a 1): ZSE -> ZSF")
        zns_util.finish_zone(all=True)
        # logging.info("ZSF -> ZSE")
        # zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("Invalid transfer for zone close: ZSE -> ZSC")
        zns_util.close_zone(all=True)
        logging.info("Invalid transfer from zone open(-a 1): ZSE -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSE -> ZSEO one by one")
        for zone in initial_zones:
            zns_util.open_zone(SLBA=zone["SLBA"])
        logging.info("ZSEO -> ZSF")
        zns_util.finish_zone(all=True)
        logging.info("ZSF -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("Invalid transfer from zone open(-a 1): ZSE -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSE -> ZSEO one by one")
        for zone in initial_zones:
            zns_util.open_zone(SLBA=zone["SLBA"])
        logging.info("ZSEO -> ZSC")
        zns_util.close_zone(all=True)
        logging.info("ZSC -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSEO -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("Invalid transfer from zone open(-a 1): ZSE -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSE -> ZSEO one by one")
        for zone in initial_zones:
            zns_util.open_zone(SLBA=zone["SLBA"])
        logging.info("ZSEO -> ZSC")
        zns_util.close_zone(all=True)
        logging.info("ZSC -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        tmp_status_internal = copy.deepcopy(initial_zones)  # refresh data
        logging.info("ZSE -> ZSIO")
        # default lba size is 4096(4k)
        for zone in initial_zones:
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zse_zsio_log.log")
            tmp_status_internal[initial_zones.index(zone)]["State"] = "0x20"  # ZSIO
            tmp_status_internal[initial_zones.index(zone)]["WP"] = hex(int(zone["SLBA"], 16) + 256)  # 1m = 256 * 4k            
            #need to be deleted since Cap should not be changed by write - changed
            tmp_status_internal[initial_zones.index(zone)]["Cap"] = zone["Cap"]  # 1m = 256 * 4k
        zns_util.report_zones(check_list=tmp_status_internal)
        logging.info("ZSIO -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("Invalid transfer from zone open(-a 1): ZSE -> ZSEO")
        zns_util.open_zone(all=True)
        logging.info("ZSE -> ZSEO one by one")
        for zone in initial_zones:
            zns_util.open_zone(SLBA=zone["SLBA"])
        logging.info("ZSEO -> ZSC")
        zns_util.close_zone(all=True)
        
        tmp_status_internal = copy.deepcopy(initial_zones)  # refresh data
        logging.info("ZSC -> ZSIO")
        for zone in initial_zones:
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zsc_zsio_log.log")
            tmp_status_internal[initial_zones.index(zone)]["State"] = "0x20"  # ZSIO
            tmp_status_internal[initial_zones.index(zone)]["WP"] = hex(int(zone["SLBA"], 16) + 256) # 1M
            #need to be deleted since Cap should not be changed by write - changed
            tmp_status_internal[initial_zones.index(zone)]["Cap"] = zone["Cap"]  # 1m = 256 * 4k
        zns_util.report_zones(check_list=tmp_status_internal)
        logging.info("ZSIO -> ZSC")
        zns_util.close_zone(all=True)
        
        logging.info("ZSC -> ZSIO")
        for zone in initial_zones:
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size + 1048576), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zsc_zsio_log_2.log")
        logging.info("ZSIO -> ZSF")
        zns_util.finish_zone(all=True)
        
        logging.info("ZSF -> ZSE")
        zns_util.reset_zone(check_list=initial_zones, all=True)
        logging.info("ZSE -> ZSIO")
        # default lba size is 4096(4k)
        for zone in initial_zones:
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size="1m", bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=60, log_folder=fio_log_folder, log_str="zse_zsio_log_2.log")
        logging.info("Invalid transfer from zone open(-a 1): ZSIO -> ZSEO")
        zns_util.open_zone(all=True)
        
        if build == "E2e":
            logging.info("Env cleanup: format the NS")
            fvt_adm_cmd_common.fvt_adm(controller, namespace).format(format_lbaf="1")
        
        test_result = "Pass"
        
    @pytest.mark.timeout(timeout=600, method="signal")
    def test_zns_append_command(self, controller, namespace, build):
        '''
        ZNS management append command
        Covering all state transition including error scenarios
        '''
        global test_result
        fio_log_folder = "zns_append_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)  
            
        logging.info("##########Start test of ZNS Append##########")
        logging.info("Basic append test on each zone")
        for zone in initial_zones:
            # size_to_append: size in block
            zns_util.append_zone(size_to_append="0x2", SLBA=zone["SLBA"], check_after=True)
        
        logging.info("Zone append for scenario Zone Is Full")
        zns_util.finish_zone(all=True)
        
        for zone in initial_zones:
            # size_to_append: size in block
            zns_util.append_zone(size_to_append="0x2", SLBA=zone["SLBA"], check_after=True, expected_error="ZONE_IS_FULL")
        
        if build == "E2e":
            logging.info("Env cleanup: format the NS")
            fvt_adm_cmd_common.fvt_adm(controller, namespace).format(format_lbaf="1")
        test_result = "Pass"
        
    @pytest.mark.timeout(timeout=300, method="signal")
    def test_specified_error_status(self):
        '''
        ZNS Command Specific Status Value:
        Write
        Zone Boundary Error: The command specifies logical blocks in more than one zone.
        Zone Is Full: The accessed zone is in the ZSF:Full state.
        Zone Is Read Only: The accessed zone is in the ZSRO:Read Only state.
        Zone Is Offline: The accessed zone is in the ZSO:Offline state.
        Zone Invalid Write: The write to a zone was not at the write pointer.
        Below two are not supported(Since MAR/MOR is fixed at the largest value, refer to zns id-ns)
        Too Many Active Zones: The controller does not allow additional active zones.
        Too Many Open Zones: The controller does not allow additional open zones.  
        Read(No error need to be covered):
        Zone Boundary Error: The command specifies logical blocks in more than one zone.  - OZCS(Identify) is 1 which means Read can be issued across zones. 
        Zone Is Offline: The accessed zone is in the ZSO:Offline state. -- only ZSRO can be transit to offline, so cannot cover this scenario.
        '''
        global test_result
        fio_log_folder = "zns_error_status_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)  
            
        logging.info("##########Start test of ZNS Command Set Command Specific Status##########")
        logging.info("Status: Zone Invalid Write")
        for zone in initial_zones:
            zns_util.nvme_write(SLBA=(int(zone["SLBA"], 16) + 1), blocks=1, data_size_in_bytes=lba_size, expected_error="ZONE_INVALID_WRITE")
        
        logging.info("Status: Zone Boundary Error")
        for zone in initial_zones:
            size = total_block_each_zone * lba_size - lba_size * 32  # leave enough block for test
            # 128k IO size to reduce IO runtime, qd should be 1, otherwise might lead to invalid WP
            zns_util.fio_runner(ns="/dev/nvme0n1", io_type="write", size=size, bs="128k", offset=(int(zone["SLBA"], 16) * lba_size), q_depth=1, timeout=600, log_folder=fio_log_folder, log_str="fulfill_slba_{}.log".format(zone["SLBA"]))
            zns_util.nvme_write(SLBA=hex(size // lba_size + int(zone["SLBA"], 16)), blocks=31, data_size_in_bytes=(lba_size * 31))
            zns_util.nvme_write(SLBA=hex((size + 31 * lba_size) // lba_size), blocks=2, data_size_in_bytes=(lba_size * 2), expected_error="ZONE_BOUNDARY_ERROR")

        logging.info("Status: Zone Is Full")
        for zone in  initial_zones:
            zns_util.nvme_write(SLBA=hex((int(zone["SLBA"], 16) + total_block_each_zone) - 1), blocks=1, data_size_in_bytes=lba_size)
            # if a zone0 is full, the WP is equal to SLBA of zone1. If specify the SLBA(in write cmd), operation is issued to zone1.
            # To achieve ZONE_IS_FULL, the SLBA here is the SLBA of the zone
            zns_util.nvme_write(SLBA=hex((int(zone["SLBA"], 16))), blocks=1, data_size_in_bytes=lba_size, expected_error=["ZONE_IS_FULL", "LBA that exceeds the size of the namespace"])

        test_result = "Pass"
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
import sys
import subprocess
from subprocess import Popen
from subprocess import PIPE
import shlex
import time
import shutil
import logging
from sfvs.nvme import nvme
import numpy as np
from basic_function.partition_filesystem import Partition_filesystem
from basic_function.partition_filesystem import Basic_function
from sfvs.nvme.utils import Utils as utils
from set_get_feature.test_set_get_feature import Test_Set_Get_Feature
from nvme_protocol_test import *
from fvt_adm_cmd_common import fvt_adm
from nvme_protocol_test.smart_lib import SMART
import filecmp

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
izip = zip
basic = Basic_function()
PF = Partition_filesystem()
host = nvme.Host.enumerate()[0]
ctrl = host.controller.enumerate()[0]
ns = ctrl.enumerate_namespace()[0]
smart = SMART(ctrl, ns)
global flag, dev_partition_map
flag = 0
dev_partition_map = {}

def format(format_lbaf, log_path):
        adm_common = fvt_adm(ctrl, ns)
        result_log = log_path + '/format_result.log'
        result = "Fail"
        size_list0 = ['0', '9', '10', '11', '12', '13', '14', '15', '16']
        size_list1 = ['1', '2', '3', '4', '5', '6', '7', '8']
        try:
            #if project == 'vail':
            #    ret = adm_common.format(format_lbaf, 'vail')
            #else:
            ret = adm_common.format(format_lbaf)
            time.sleep(5)
            if ret == 0:
                ns_data = adm_common.ns_identify()
                if ns_data != -1:
                    flbas = ns_data.flbas
                    lba_ds = ns_data.lbaf(flbas & 0x0F).ds
                    lba_size = 2 ** lba_ds	
                    logging.info("Identify LBA size is: {}".format(lba_size))
                    
                    lba_size_refer = 0
                    
                    if format_lbaf in size_list0:  # 512 byte LBA
                        lba_size_refer = 512
                    elif format_lbaf in size_list1:
                        lba_size_refer = 4096

                    if lba_size == lba_size_refer:
                        logging.info("Format to {} LBA size successfully".format(lba_size))
                        result = "Pass"
                    else:
                        logging.error("Real lba size: {}, expected: {}".format(lba_size, lba_size_refer))
                        result = "Fail"
                    
                    if str(flbas) == str(format_lbaf):
                        logging.info("Format to flbas:{} successfully".format(flbas))
                    else:
                        logging.error("Real flbas: {}, expected: {}".format(flbas, format_lbaf))
                        result = "Fail"
                        
        except Exception as e:
            logging.error("Initialize failed:{}".format(e))
            
        with open(result_log, "w+") as f:
            f.write("Format: {}\n".format(result))

        if result == "Fail":
            pytest.fail("Format failed")

def abort(ctrl):
    try:
        with ctrl as ctrl_tmp:
            data = ctrl_tmp.abort(cid, sqid)
            logging.info(data)
    except nvme.NVMeException as e:
        logging.error("abort fail")

def get_log_page(ctrl):
    for lid in [0x02, 0x05, 0x07, 0x08]:
        try:
            with ctrl as ctrl_tmp:
                print("lid=" + str(lid))
                data = ctrl_tmp.log_page(lid, 4096)
                print(data)
        except nvme.NVMeException as e:
            logging.error("get log page [Fail] %d", lid)

def create_partition(device, device_type, log_path):
    # check to see if SATA device is detected
    global dev_partition_map
    logging.info("device is {}".format(device))
    dev_partition_map = basic.dev_partition_table(device_type, device)
    logging.info(dev_partition_map)
    logging.info("----create partition----------")
    create_partition_log_path = os.path.join(log_path, "create_partition")

    if os.path.exists(create_partition_log_path):
        shutil.rmtree(create_partition_log_path)
    if not os.path.exists(create_partition_log_path):
        os.mkdir(create_partition_log_path)
    disk_size = basic.find_keyword(device)
    if disk_size == 0:
        pytest.fail('get disk size failed')
    if not os.path.exists("/media/fte"):
        logging.info("create fte folder")
        os.mkdir("/media/fte")

    logging.info("device is {}".format(device))
    logging.info("disk_size is {}".format(disk_size))
    size_1 = int(disk_size) // 3
    logging.info("size_1 is {}".format(size_1))

    size_2 = int(disk_size) // 4
    logging.info("size_2 is {}".format(size_2))

    size_1 = str(size_1)
    size_2 = str(size_2)
    size_list = [size_1, size_2]

    for num_partition, size_of_partition in izip(range(1, len(size_list) + 1), size_list):
        logging.info("num_partition: {}, size_of_partition: {}".format(num_partition, size_of_partition))
        # basic.create_partition(device, str(num_partition), size_of_partition)
        PF.create_partition(device, "p", str(num_partition), size_of_partition)
        time.sleep(5)
    

    # partitions are requisite for following tests, if no partition or not all partitions available, following tests should be aborted.
    # Otherwise, IO will be running on local system device. 
    partition_list = PF.get_partitions(device)
    logging.debug("========{}".format(dev_partition_map))
    logging.debug("========{}".format(partition_list))
    if partition_list == []:
        pytest.fail("No available partition exist")
    else:
        for partition in dev_partition_map:
            for actual_partition in partition_list:
                if actual_partition.decode("GBK") == dev_partition_map[partition]:
                    logging.debug("match")
                    break
                if partition_list.index(actual_partition) == len(partition_list) - 1:
                    pytest.fail("Not all required partitions exist")
            
    for partition in dev_partition_map:
        logging.info("partition:{}, value:{}".format(partition, dev_partition_map[partition]))
        # basic.mount_partition(dev_partition_map[partition], partition)
        ret = PF.config_fs(dev_partition_map[partition].encode(), 'ext4')
        if ret == -1:
            pytest.fail("config fs failed")
        ret = PF.mount_partition(dev_partition_map[partition].encode(), "/media/fte/" + partition)
        if ret == -1:
            pytest.fail("mount failed")

    for partition in dev_partition_map:
        basic.change_permission(partition)


def delete_partition(device, device_type, log_path):
    disk_partition = 0
    disk1_partition = 0
    disk2_partition = 0
    global dev_partition_map
    logging.info("device is {}".format(device))
    dev_partition_map = basic.dev_partition_table(device_type, device)
    logging.info(dev_partition_map)
    logging.info("----delete partition----------")

    delete_partition_log_path = os.path.join(log_path, "delete_partition")

    if os.path.exists(delete_partition_log_path):
        shutil.rmtree(delete_partition_log_path)

    if not os.path.exists(delete_partition_log_path):
        os.mkdir(delete_partition_log_path)

    # 1. check the mount partition
    os.system("sudo mount -l > mount_disk.txt")
    with open("./mount_disk.txt", "r+") as mount_log:
        data = mount_log.readlines()
        for i in range(len(data)):
            if "/dev/nvme0n1p1 " in data[i]:
                disk1_partition = 1
            elif "/dev/nvme0n1p2 " in data[i]:
                disk2_partition = 1

    disk_partition = disk1_partition + disk2_partition
    # 2. partition1 and partition2 are found, delete the mounted partition folder and umount the disk partitions.
    if disk_partition == 2:
        for partition in dev_partition_map:
            logging.info("partition:{}, value:{}".format(partition, dev_partition_map[partition]))
            basic.unmount_partition(dev_partition_map[partition], partition)
        for num_partition in range(1, len(dev_partition_map) + 1):
            logging.info("num_partition: {}".format(num_partition))
            basic.delete_partition(device, str(num_partition))
    shutil.rmtree(delete_partition_log_path)
    time.sleep(5)


def delete_operation(log_path):
    logging.info("--------------delete operation----------------")
    delete_operation_log_path = os.path.join(log_path, "delete_operation")

    if os.path.exists(delete_operation_log_path):
        shutil.rmtree(delete_operation_log_path)

    if not os.path.exists(delete_operation_log_path):
        os.mkdir(delete_operation_log_path)

    loglist = os.listdir("/media/fte/partition_1")
    logging.info(loglist)
    for log in loglist:
        if log.endswith(".log"):
            source_file = "/media/fte/partition_1/file_write.log"
            os.remove(source_file)
            logging.info("delete operation is done successfully.")
    shutil.rmtree(delete_operation_log_path)

def find_host():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name


@pytest.fixture(scope="module")
def device(device_type):
    logging.info('device_type: {}'.format(device_type))
    device = basic.find_dev(device_type)
    yield device

@pytest.fixture(scope="module")
def log_path():
    hostname = find_host()
    log_path = os.path.join(os.path.dirname(__file__), hostname+"_function_check_logs")

    if os.path.exists(log_path):
        shutil.rmtree(log_path)
    os.mkdir(log_path)

    yield log_path
    os.system('mv *.log '+log_path)

def test_detect_device(device):
    logging.info("---test detect device------------------------")
    global flag

    if device != -1:  # if no device found, -1 returned
        logging.info("device is {}".format(device))
    else:
        flag = device

    if flag == -1:
        pytest.fail('Device detect failed')
    else:
        logging.info("detect device success.")

def test_identify(device, device_type, log_path):
    identify_log_path = os.path.join(log_path, "identify")
    if os.path.exists(identify_log_path):
        shutil.rmtree(identify_log_path)

    if not os.path.exists(identify_log_path):
        os.mkdir(identify_log_path)

    host = nvme.Host.enumerate()[0]
    ctrl = host.controller.enumerate()[0]
    ns = ctrl.enumerate_namespace()[0]
    ctrl.open()
    ns.open()
    logging.info("device is {}".format(device))
    if device_type == "nvme":
        ret1 = NVMeAdmin_CNS_00h_Identify.main(ctrl, ns, identify_log_path)
        ret2 = NVMeAdmin_CNS_00h_Verify_NVMe_Capacity.main(ctrl, ns, identify_log_path)
        ret3 = NVMeAdmin_CNS_01h_Identify.main(ctrl, ns, identify_log_path)
        ret4 = NVMeAdmin_CNS_02h_Identify.main(ctrl, ns, identify_log_path)
        ret5 = NVMeAdmin_CNS_03h_identify.main(ctrl, ns, identify_log_path)
        ret6 = NVMeAdmin_CNS_FFh_identify.main(identify_log_path)
    if ret1 == "FAILED":
        pytest.fail("NVMeAdmin_CNS_00h_Identify FAILED")
    if ret2 == "FAILED":
        pytest.fail("NVMeAdmin_CNS_00h_Verify_NVMe_Capacity FAILED")
    if ret3 == "FAILED":
        pytest.fail("NVMeAdmin_CNS_01h_Identify FAILED")
    if ret4 == "FAILED":
        pytest.fail("NVMeAdmin_CNS_02h_Identify FAILED")
    if ret5 == "FAILED":
        pytest.fail("NVMeAdmin_CNS_03h_Identify FAILED")
    if ret6 == "FAILED":
        pytest.fail("NVMeAdmin_CNS_FFh_Identify FAILED")

def test_format_NVM(log_path):
    logging.info("---test format NVMe------------------------")
    ctrl.open()
    ns.open()
    format_lbaf = "0"
    format_log_folder = os.path.join(log_path, "format")
    if os.path.exists(format_log_folder):
        shutil.rmtree(format_log_folder)

    if not os.path.exists(format_log_folder):
        os.mkdir(format_log_folder)
    format(format_lbaf, format_log_folder)

def test_smart_test(device, device_type, log_path):
    logging.info("---test smart test------------------------")
    smart_log_path = os.path.join(log_path, "smart")
    if os.path.exists(smart_log_path):
        shutil.rmtree(smart_log_path)

    if not os.path.exists(smart_log_path):
        os.mkdir(smart_log_path)

    host = nvme.Host.enumerate()[0]
    ctrl = host.controller.enumerate()[0]
    ns = ctrl.enumerate_namespace()[0]
    ctrl.open()
    ns.open()
    logging.info("device is {}".format(device))
    if device_type == "nvme":
        ret1 = NVMeSmart_dataunitread.main(ctrl, ns, smart_log_path)
        ret2 = NVMeSmart_dataunitwrite.main(ctrl, ns, smart_log_path)
        ret3 = NVMeSmart_Host_Write_Commands.main(ctrl, ns, smart_log_path)
        ret4 = NVMeSmart_Host_Read_Commands.main(ctrl, ns, smart_log_path)
        ret5 = NVMeSmart_STANDARD_Percentage_Used.main(smart_log_path)
        ret6 = NVMeSmart_STANDARD_Available_Spare.main(smart_log_path)
        ret7 = NVMeSmart_STANDARD_Media_Error.main(smart_log_path)
        ret8 = NVMeSmart_STANDARD_Ctrl_Busy_Time.main(smart_log_path)
        ret9 = NVMeSmart_STANDARD_Available_Spare_Threshold.main(smart_log_path)
        ret10 = NVMeSmart_STANDARD_Critical_Warning.main(smart_log_path)
        # ret13-ret22 may due to the case design will set features which fw can't support till now(2021.11.17)
        '''
        ret13 = NVMeSmart_Composite_Temperature.main(ctrl, ns, smart_log_path)
        ret14 = NVMeSmart_Num_Err_Entries.main(ctrl, ns, smart_log_path)
        ret15 = NVMeSmart_Temperature_Sensor.main(ctrl, ns, smart_log_path)
        ret16 = NVMeSmart_Thm_Temp1_Total_Time.main(ctrl, ns, smart_log_path)
        ret17 = NVMeSmart_Thm_Temp2_Total_Time.main(ctrl, ns, smart_log_path)
        ret18 = NVMeSmart_Thm_Temp1_Trans_Count.main(ctrl, ns, smart_log_path)
        ret19 = NVMeSmart_Thm_Temp2_Trans_Count.main(ctrl, ns, smart_log_path)
        ret20 = NVMeSmart_Critical_Composite_Temp_Time.main(ctrl, ns, smart_log_path)
        ret21 = NVMeSmart_Warning_Composite_Temp_Time.main(ctrl, ns, smart_log_path)
        ret22 = NVMeSmart_Media_Data_Integrity_Errors.main(ctrl, ns, smart_log_path)
        '''

        # OCP Smart
        # Because FW don't support until now (2021.11.17), Only run test cases and don't check result
        '''
        ret101 = NVMeSmart_OCP_Physical_Media_Units_Written.main(ctrl, ns, smart_log_path)
        ret102 = NVMeSmart_OCP_Physical_Media_Units_Read.main(ctrl, ns, smart_log_path)
        ret103 = NVMeSmart_OCP_Bad_User_Nand_Blocks.main(ctrl, ns, smart_log_path)
        ret104 = NVMeSmart_OCP_Bad_System_Nand_Blocks.main(ctrl, ns, smart_log_path)
        ret105 = NVMeSmart_OCP_XOR_Recovery_Count.main(ctrl, ns, smart_log_path)
        ret106 = NVMeSmart_OCP_Uncorrectable_Read_Error_Count.main(ctrl, ns, smart_log_path)
        ret107 = NVMeSmart_OCP_Soft_ECC_Error_Count.main(ctrl, ns, smart_log_path)
        ret108 = NVMeSmart_OCP_End_to_End_Correction_Counts.main(ctrl, ns, smart_log_path)
        ret109 = NVMeSmart_OCP_System_Data_Used_Percentange.main(ctrl, ns, smart_log_path)
        ret110 = NVMeSmart_OCP_Refresh_Counts.main(ctrl, ns, smart_log_path)
        ret111 = NVMeSmart_OCP_User_Data_Erase_Counts.main(ctrl, ns, smart_log_path)
        ret112 = NVMeSmart_OCP_Thermal_Throttling_Status_and_Count.main(ctrl, ns, smart_log_path)
        ret113 = NVMeSmart_OCP_NVMe_SSD_Specification_Version.main(ctrl, ns, smart_log_path)
        ret115 = NVMeSmart_OCP_Incomplete_Shutdowns.main(ctrl, ns, smart_log_path)
        ret117 = NVMeSmart_OCP_Free_Blocks_Percentage.main(ctrl, ns, smart_log_path)
        ret119 = NVMeSmart_OCP_Capacitor_Health.main(ctrl, ns, smart_log_path)
        ret120 = NVMeSmart_OCP_NVMe_Errata_Version.main(ctrl, ns, smart_log_path)
        ret121 = NVMeSmart_OCP_Unaligned_IO.main(ctrl, ns, smart_log_path)
        ret122 = NVMeSmart_OCP_Security_Version_Number.main(ctrl, ns, smart_log_path)
        ret123 = NVMeSmart_OCP_Total_NUSE.main(ctrl, ns, smart_log_path)
        ret124 = NVMeSmart_OCP_PLP_Start_Count.main(ctrl, ns, smart_log_path)
        ret125 = NVMeSmart_OCP_Endurance_Estimate.main(ctrl, ns, smart_log_path)
        ret126 = NVMeSmart_OCP_Log_Page_Version.main(ctrl, ns, smart_log_path)
        ret127 = NVMeSmart_OCP_Log_Page_GUID.main(ctrl, ns, smart_log_path)
        ret130 = NVMeSmart_OCP_Reserved.main(ctrl, ns, smart_log_path)
        ret131 = NVMeSmart_OCP_Power_State_Change_Count.main(ctrl, ns, smart_log_path)
        '''

    if ret1 == "FAILED":
        pytest.fail("NVMeSmart_dataunitread FAILED")
    if ret2 == "FAILED":
        pytest.fail("NVMeSmart_dataunitwrite FAILED")
    if ret3 == "FAILED":
        pytest.fail("NVMeSmart_Host_Write_Commands FAILED")
    if ret4 == "FAILED":
        pytest.fail("NVMeSmart_Host_Read_Commands FAILED")
    #if ret5 == "FAILED":
    #   pytest.fail("Percentage Used FAILED")
    #if ret6 == "FAILED":
    #   pytest.fail("Available Spare FAILED")
    #if ret8 == "FAILED":
    #   pytest.fail("Controller Busy Time FAILED")
    #smart_tests.smart_test.smart_percentage_used(prepare_device_conf, size)
    

def test_create_delete_partition(device, cfg):
    logging.info("-----test_create_delete_partition---------")
    logging.info("device is {}".format(device))
    # for runtime log
    if os.path.exists('create_delete.log'):
        os.rename('create_delete.log', 'create_delete_bak.log')
    LOGGER = logging.getLogger()
    LOGGER.setLevel(logging.INFO)
    FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
    run_log = "fs_log.log"
    handler = logging.FileHandler(run_log)
    handler.setFormatter(FORMATTER)
    LOGGER.addHandler(handler)
    PF = Partition_filesystem()
    case = basic.get_case(cfg)
    case_name = ''
    pri_par = ''
    log_par = ''
    fs_type = ''
    for item in case:
        case_name = item[0]
        pri_par = item[1][1]
        log_par = item[2][1]
        fs_type = item[3][1]
        logging.info([case_name, pri_par, log_par, fs_type])
        result = PF.run_partition_filesystem([case_name, pri_par, log_par, fs_type], device)
        if result == -1:
            pytest.fail('Test create delete partition failed!')
        # this need to improve, need check the device is not busy then run filesystem
        time.sleep(60)

def test_seqwrite_operation(device, device_type, log_path):
    create_partition(device, device_type, log_path)
    flag = 0
    logging.info("Sequential Write in Full Disk.")
    logging.info("device is {}".format(device))
    pattern_list = ["0x55AA55AA", "0xAA55AA55", "0xFF00", "0xFF"]

    sequential_write_log_path = os.path.join(log_path, "sequential_write")

    if os.path.exists(sequential_write_log_path):
        shutil.rmtree(sequential_write_log_path)

    if not os.path.exists(sequential_write_log_path):
        os.mkdir(sequential_write_log_path)

    disk_size = basic.find_keyword(device)

    logging.info("disk_size is {}".format(disk_size))
    try:
        for pattern in pattern_list:

            for partition in dev_partition_map:
                file_log = os.path.join(os.path.dirname(__file__),
                                        "fio_tool_result_seqwr_" + pattern + "_"+partition + ".log")
                logging.info(file_log)
                # fio running time and size need to write at cfg file.

                logging.info("------start fio test-----------------------------------------")
                logging.info("partition:{}, value:{}".format(partition, dev_partition_map[partition]))

                cmd = "sudo fio --name=seqwr --runtime=120 --ioengine=libaio --direct=1 --buffered=0 --offset=0 \
                    --size={} --continue_on_error=none --bs=128k --iodepth=32 --rw=write --filename={} --output={} --do_verify=1 \
                    --verify_dump=1 --verify=md5 --verify_fatal=1 \
                    --verify_pattern={} ".format("20G", "/media/fte/"+partition+"/test_"+pattern+"_"+partition, file_log, pattern)

                logging.info("cmd is {}.".format(cmd))

                args = shlex.split(cmd)
                process = subprocess.Popen(args, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                out, err = process.communicate()
                os.system("sudo chmod 777 {}".format(file_log))

                with open(file_log, "r+") as log_file:
                    while True:
                        data = log_file.readline()
                        if "err=" in data:
                            if "0" not in data:
                                logging.error("error happened")
                                flag = 1
                                pytest.fail('Test seqwrite operation failed!')
                            else:
                                break
                #log_file.close()
                subprocess.check_call(["mv", file_log, sequential_write_log_path])
                process.terminate()
                source_file = "/media/fte/"+partition+"/test_"+pattern+"_"+partition
                os.remove(source_file)
    except ValueError as error_message:
        logging.error(error_message)
        pytest.fail('Test seqwrite operation failed!')

def test_copy_operation(device, device_type, log_path):
    logging.info("------test copy operation------")
    source_file = "/media/fte/partition_1/file_write.log"

    copy_operation_log_path = os.path.join(log_path, "copy_operation")

    if os.path.exists(copy_operation_log_path):
        shutil.rmtree(copy_operation_log_path)

    if not os.path.exists(copy_operation_log_path):
        os.mkdir(copy_operation_log_path)

    if os.path.exists(source_file):
        logging.info("remove: source_file: {}".format(source_file))
        shutil.rmtree(source_file)

    if not os.path.exists(source_file):
        logging.info("no source_file: {}".format(source_file))
        with open(source_file, "w+") as file_generate:
            for i in range(10):
                file_generate.write("Write file {}\r\n".format(i))

        target_file = os.path.join(os.getcwd(), "source.log")
        logging.info("source_file is {0}, target_file is {1}".format(source_file, target_file))
        try:
            shutil.copyfile(source_file, target_file)
        except IOError as error_message:
            logging.error(error_message)
            pytest.fail('Copy operation failed!')
        logging.info("copy operation is done successfully.")
        file_generate.close()

def test_compare_operation(device, device_type, log_path):
    logging.info("------test compare operation------")
    source_file = "/media/fte/partition_1/file_write.log"
    target_file = os.path.join(os.getcwd(), "source.log")

    copy_operation_log_path = os.path.join(log_path, "copy_operation")

    if not os.path.exists(copy_operation_log_path):
        os.mkdir(copy_operation_log_path)

    if not os.path.exists(source_file):
        logging.info("no source_file: {}".format(source_file))
        with open(source_file, "w+") as file_generate:
            for i in range(10):
                file_generate.write("Write file {}\r\n".format(i))
        file_generate.close()
    
    logging.info("source_file is {0}, target_file is {1}".format(source_file, target_file))
    if not os.path.exists(target_file):
        try:
            shutil.copyfile(source_file, target_file)
        except IOError as error_message:
            logging.error(error_message)
            pytest.fail('Copy operation failed!')
        logging.info("copy operation is done successfully.")
    
    logging.info('Compare source_file and target_file files')
    if not filecmp.cmp(source_file,target_file):
        logging.error('Compare small files failed, please check')
        delete_operation(log_path)
        delete_partition(device, device_type, log_path)
        pytest.fail('Compare operation failed!') 
    else:
        logging.info('Compare operation PASSED')

    delete_operation(log_path)
    delete_partition(device, device_type, log_path)  
    shutil.rmtree(copy_operation_log_path) 

def test_get_log_page(device):
    logging.info("---test get log page------------------------")
    host = nvme.Host.enumerate()[0]
    ctrl = host.controller.enumerate()[0]
    if device != -1:  # if no device found, -1 returned
        logging.info("device is {}".format(device))
        get_log_page(ctrl)

def test_set_get_features():
    logging.info("---test set_get_features------------------------")
    Test_Set_Get_Feature()


def test_detect_device(device):
    logging.info("---test detect device------------------------")
    global flag

    if device != -1:  # if no device found, -1 returned
        logging.info("device is {}".format(device))
    else:
        flag = device

    if flag == -1:
        pytest.fail('Device detect failed')
    else:
        logging.info("detect device success.")
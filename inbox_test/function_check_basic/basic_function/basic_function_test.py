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
from partition_filesystem import Partition_filesystem
from partition_filesystem import Basic_function

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
izip = zip
basic = Basic_function()
PF = Partition_filesystem()

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


def find_host():
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name


class Test_Basic_IO:
    global flag, dev_partition_map
    flag = 0
    dev_partition_map = {}

    @pytest.fixture(scope="module")
    def device(self, device_type):
        logging.info('device_type: {}'.format(device_type))
        device = basic.find_dev(device_type)
        yield device

    @pytest.fixture(scope="module")
    def log_path(self):
        hostname = find_host()
        log_path = os.path.join(os.path.dirname(__file__), hostname+"_basic_function_logs")

        if os.path.exists(log_path):
            shutil.rmtree(log_path)
        os.mkdir(log_path)

        yield log_path
        os.system('mv *.log '+log_path)

    def test_detect_device(self, device):
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

    def test_identify(self, device, device_type):
        logging.info("---test identify------------------------")
        logging.info("device is {}".format(device))
        if device_type == "nvme":
            logging.info("nvme drive identify data/Capacity/SN info")
            basic.nvme_identify()
            logging.info('nvme identify test done')

    def test_create_delete_partition(self, device, cfg, log_path):
        logging.info("-----test_create_delete_partition---------")
        logging.info("device is {}".format(device))
        # for runtime log
        if os.path.exists('fs_log.log'):
            os.rename('fs_log.log', 'fs_log_bak.log')
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

    def test_seqwrite_operation(self, device, device_type, log_path):
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

    def test_copy_operation(self, device, device_type, log_path):
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
            delete_operation(log_path)
            delete_partition(device, device_type, log_path)
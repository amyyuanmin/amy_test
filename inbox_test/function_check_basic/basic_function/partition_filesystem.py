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
from subprocess import Popen, PIPE, STDOUT
import re
import shlex
import os
from configparser import ConfigParser
from itertools import combinations
import time
import time
import shutil
import glob
import filecmp
import logging
from datetime import datetime
from datetime import timedelta
from sfvs.nvme import nvme
#from configparser import ConfigParser
import sys
import pexpect

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')


class Basic_function:
    def get_case(self, config_file):
        fs_type = []  # all file system types
        all_case = []
        config = ConfigParser()
        config.read(config_file)
        sections = config.sections()
        fs_type = config.get("File System Type", "fs_type").split(",")
        for section in sections:
            if section != "File System Type":
                #partition_num = int(config.get(section, 'primary_partition')) + int(config.get(section, 'logical_partition'))
                #int(config.get(section, 'logical_partition'))
                all_config = config.items(section)
                for fs in fs_type:
                    each_case = []
                    case_name = section+"_"+fs
                    each_case.append(case_name)
                    each_case.extend(all_config)
                    each_case.append(("fs_type", fs))
                    all_case.append(each_case)
        return all_case

    def dev_partition_table(self, device_type, device):
        partition_1 = "partition_1"
        partition_2 = "partition_2"
        logging.info("partition_1 is {}".format(partition_1))
        dev_partition_map = {}
        logging.info("Found the device, and it is {}".format(device))
        if device == " ":
            logging.error("device cannot be found")
            sys.exit()
        if device_type == "sata":
            dev_partition_map[partition_1] = device + "1"
            dev_partition_map[partition_2] = device + "2"
        elif device_type == "nvme":
            logging.info(partition_1)
            logging.info(device)
            dev_partition_map[partition_1] = device + "p1"
            dev_partition_map[partition_2] = device + "p2"
        return dev_partition_map

    def create_partition(self, device, partition, size_of_partition):
        logging.info("device is {}".format(device))
        cmd = "sudo fdisk " + device
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        p.stdin.write("n\n".encode("GBK"))
        p.stdin.write("p\n".encode("GBK"))
        p.stdin.write(partition.encode("GBK") + "\n".encode("GBK"))
        p.stdin.write(" \n".encode("GBK"))
        p.stdin.write("+".encode("GBK") + size_of_partition.encode("GBK") + "G\n".encode("GBK"))
        p.stdin.write("w\n".encode("GBK"))
        p.stdin.close()
        p.terminate()

    def delete_partition(self, device, partition):
        logging.info("device is {}".format(device))
        cmd = "sudo fdisk " + device
        logging.info("delete cmd is {}".format(cmd))
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        p.stdin.write("d\n".encode("GBK"))
        logging.info("partition is {}".format(partition))

        p.stdin.write(partition.encode("GBK") + "\n".encode("GBK"))
        p.stdin.write("w\n".encode("GBK"))
        p.stdin.close()
        p.terminate()

    def mount_partition(self, device, label):
        cmd = "sudo mkfs -t ext4 " + device
        logging.info("cmd is {}".format(cmd))
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        #p.stdin.write("y\n".encode("GBK"))
        #p.stdin.close()
        #p.terminate()
        time.sleep(30)
        create_dirs = "sudo mkdir /media/fte/" + label
        os.system(create_dirs)
        mount_cmd = "sudo mount -t ext4 " + device + " /media/fte/" + label
        logging.info(mount_cmd)
        os.system(mount_cmd)
        logging.info("mount partition is done")

    def unmount_partition(self, device, label):
        logging.info("Check the device mount list")
        cmd = "sudo umount " + device
        logging.info("cmd is {}".format(cmd))
        args = shlex.split(cmd)
        count=1
        max_count=3
        while (count <= max_count):
            p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
            logging.info(p.stderr.read())
            logging.info(p.stdout.read())
            p.terminate()
            if p.stderr.read():
                logging.info("unmount partition met error!!!!")
                count += 1
                continue
            else:
                logging.info("unmount partition is done")
                break
        time.sleep(10)
        delete_dirs = "sudo rm -r /media/fte/" + label
        logging.info("cmd is {}".format(delete_dirs))
        os.system(delete_dirs)
        logging.info("remove mount folder")

    def change_permission(self, partition):
        cmd = "sudo chmod -R 777 /media/fte/" + partition
        os.system(cmd)
        logging.info("permission setting is done.")

    def copy_file_to_partition(self, partition):
        source_folder = "./1/"
        target_folder = "/media/fte/" + partition + "/1"
        shutil.copytree(source_folder, target_folder)

    def copy_file_from_one_partition_to_another_partition(self, source_folder, target_folder):
        shutil.copytree(source_folder, target_folder)

    def remove_all_files(self, partition):
        target_folder = "/media/fte/" + partition + "/2"
        logging.info("target_folder is {}".format(target_folder))
        if os.path.exists(target_folder):
            shutil.rmtree(target_folder)

    def compare_file(self, fileobj, source_folder, target_folder):
        comparison_flag = 0
        comparison = filecmp.dircmp(source_folder, target_folder)
        # comparison.report_full_closure()
        if len(comparison.diff_files) > 0:
            logging.info("diff file is {}".format(comparison.diff_files))
            comparison_flag = 1
        if len(comparison.left_only) > 0:
            logging.info("file left only is {}".format(comparison.left_only))
            comparison_flag = 2
        if len(comparison.right_only) > 0:
            logging.info("file right only is {}".format(comparison.right_only))
            comparison_flag = 3
        if comparison_flag > 0:
            fileobj.write(self.print_local_time() + "left folder is {}\r\n".format(source_folder))
            fileobj.write(self.print_local_time() + "right folder is {}\r\n".format(target_folder))
            fileobj.write(self.print_local_time() + "1 means diff file, 2 means left only and 3 means right only\r\n")
            fileobj.write(self.print_local_time() + "failed is {}\r\n".format(comparison_flag))
        return comparison_flag

    def print_local_time(self):
        time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return time

    def run_small_file_comparison_test(self, fileobj, count, partition_list, source_folder_list, target_folder_list):
        for partition, source_folder, target_folder in zip(partition_list, source_folder_list, target_folder_list):
            logging.info("partition:{}, source_folder:{}, target_folder:{}".format(partition, source_folder, target_folder))
            self.copy_file_from_one_partition_to_another_partition(source_folder, target_folder)

            flag = self.compare_file(fileobj, source_folder, target_folder)
            if flag > 0:
                break
            logging.info("clean all folder")
            self.remove_all_files(partition)

        fileobj.write(self.print_local_time() + "count is {}\r\n".format(count))
        return flag

    def find_keyword(self, device):
        os.system("sudo fdisk -l " + device + " > disk_size.log")

        checkfile = open('disk_size.log', "r")
        while True:
            keyword = checkfile.readline()
            logging.info("keyword: {}".format(keyword))
            if 'GiB' in keyword:
                index = keyword.find("GiB")
                end_index = index - 1
                #start_index = end_index - 6
                start_index = keyword.find(":") + 1
                # cannot convert string with '.' to int directly, use float for agent
                disk_size = int(float(keyword[start_index:end_index].strip()))
                logging.info("disk_size is {}".format(disk_size))
                break
            elif 'TiB' in keyword:
                index = keyword.find("TiB")
                end_index = index - 1
                start_index = keyword.find(":") + 1
                disk_size = int(float(keyword[start_index:end_index].strip())) * 1024
                logging.info("disk_size is {}".format(disk_size))
                break
            if not keyword:
                disk_size = 0
                break

        checkfile.close()
        return disk_size

    def find_dev(self, disk_type):
        params = ("KINGSTON")
        if disk_type == "sata":
            device = "/dev/sdb"  # need confirm with Dean
            os.system("lsscsi > scsi.log")
            checkfile = open("scsi.log", "r")
            while True:
                keyword = checkfile.readline()
                logging.info(keyword)

                if params in keyword:
                    logging.info("find KINGSOTN device")
                    if self.check_device(disk_type):
                        logging.info("check device, have device")
                        break
                    else:
                        logging.info("check device, return no sata device")
                        return -1

            checkfile.close()

        elif disk_type == "nvme":
            device = "/dev/nvme0n1"
            logging.info(device)
            process = Popen(["sudo", "nvme", "list"], stdout=PIPE)
            out, _ = process.communicate()
            logging.info(out)
            process.terminate()
            if(device in str(out)):
                logging.info("Found nvme device")
            else:
                logging.info("---Failed to find nvme device-----------")
                return -1
        return device

    def check_device(self, disk_type):
        process = Popen(["sudo", "fdisk", "-l"], stdout=PIPE)
        out, _ = process.communicate()
        logging.info(out)
        process.terminate()
        if disk_type == "sata":
            if not ("/dev/sdb" in str(out)):
                logging.info("Cannot find the second sata disk")
                return -1
        if disk_type == "nvme":
            if not ("/dev/nvme0n1" in str(out)):
                logging.info("Cannot find nvme disk")
                return -1
        logging.info("find nvme---------")

    def nvme_identify(self):
        # just read info, no check
        # check_flag=0
        # Find First NVme device in host
        host = nvme.Host.enumerate()[0]
        # get controller device
        ctrl = host.controller.enumerate()[0]
        try:
            with ctrl:
                # Query Controller Identify data and logging.info
                data = ctrl.identify()
                logging.info("sn is: {}".format(data.sn))
                logging.info("mn is: {}".format(data.mn))
                logging.info("fr is: {}".format(data.fr))

            # Find first namespace device of first NVMe device
            ns = ctrl.enumerate_namespace()[0]
            with ns:
                # Query Identify data of namespace and print it
                data = ns.identify()
                logging.info('sector is: {}'.format(data.ncap))
                logging.info('namespace id:{}'.format(ns.ident))
        except nvme.NVMeException as e:
            logging.error('Error: {}'.format(str(e)))


class Partition_filesystem:
    def __init__(self):
        self.output = None

    def send_cmd_with_expect(self, child, cmd, indicator, expect = ''):
        '''
        @param: child - pexpect instance
        @param: expect - expected prompt before next cmd, if need to do verification for some keyword, specify here
        @param: cmd - cmd to be executed
        '''
        self.output = child.before.decode("GBK")
        if expect in self.output:
            logging.info("cmd is: {}".format(cmd))
            child.sendline(cmd)
            child.expect([indicator, pexpect.EOF])
            self.output = child.before.decode("GBK")
            logging.debug("output: {}".format(self.output))
        else:
            pass

    def create_partition(self, dut, partition_type, partition_number, size_of_partition):
        # return: 0 for success and -1 for fail
        logging.info("partition_type is:{} , partition_number is: {} , size_of_partition is: {}".format(partition_type, partition_number, size_of_partition))
        os.system("partprobe {}".format(dut))
        cmd = "sudo fdisk " + dut
        logging.info("cmd is {}".format(cmd))
        child = pexpect.spawn(cmd)
        child.expect(":")
        self.send_cmd_with_expect(child, 'n', ":")
        if partition_type == 'l':
            self.send_cmd_with_expect(child, partition_type, ":")  # no partition number required for logical partition
        elif partition_type == 'p' and partition_number == '4':
            # if it's the 4th parimary partition, no need to specified the number
            self.send_cmd_with_expect(child, partition_type, ":")
        else:
            self.send_cmd_with_expect(child, partition_type, ":")
            self.send_cmd_with_expect(child, partition_number, ":")
        self.send_cmd_with_expect(child, " ", ":")
        if size_of_partition != ' ':  # if specify the size of partition
            self.send_cmd_with_expect(child, "+" + size_of_partition + "G", ":")
        else:  # if use default partition size, usually for the extended partition
            self.send_cmd_with_expect(child, " ", ":")
            size_of_partition = 'full or the rest of all'
        self.send_cmd_with_expect(child, "Y", ":", "signature")
        self.send_cmd_with_expect(child, "w", ":")
        if partition_type == 'p':
            p_type = "primary"
        elif partition_type == 'e':
            p_type = "extended"
        elif partition_type == 'l':
            p_type = "logical"
        if "error" in self.output:
            #logging.error('Create partition failed, error output: {}'.format(lines))
            logging.info("----------------------------fail---------------")
            logging.info(self.output)
            return -1
        else:
            if partition_type == 'l':
                logging.info("Create a {} partition, the size is {} GiB".format(p_type, size_of_partition))
            else:
                logging.info("Create a {} partition with number {} and size {} GiB".format(
                    p_type, partition_number, size_of_partition))
        return 0

    def config_fs(self, partition, fs_type):
        # return: 0 for success and -1 for fail
        cmd = "sudo mkfs -t " + fs_type + ' ' + partition.decode()
        logging.info('config-fs: '+cmd)
        child = pexpect.spawn(cmd)
        child.expect(["\?", pexpect.EOF])
        self.send_cmd_with_expect(child, "y", "\?", "Proceed anyway")
        
        logging.info("Configure partition {} to file system {}".format(partition, fs_type))
        logging.info("Config output: \n{}".format(self.output))

        time.sleep(5)  # wait 5 sec to check, found that if check immediately, no file system info listed
        check_cmd = 'lsblk -f ' + partition.decode()
        args = shlex.split(check_cmd)
        p = Popen(args, stdout=PIPE, stderr=STDOUT)
        out = p.stdout.readlines()
        fs_type_temp = ''
        logging.info("Check file system configure result..")
        p.terminate()
        for line in out:
            # partition is like /dev/nvme0n1p1, but the output is without /dev/
            tmp = re.search(b'.*'+partition[5:]+b'\s(.*)\s.*\s', line)
            if tmp != None:
                logging.debug('tmp.group(): {} '.format(tmp.group()))
                fs_type_temp = tmp.group(1).decode().strip()
        logging.debug('tmp.group(1): '+fs_type_temp)
        if fs_type == 'msdos' or fs_type == 'fat':
            fs_type = 'vfat'
        if fs_type not in fs_type_temp:
            logging.error("Configure file system failed. Actual fs: {}".format(fs_type_temp))
            return -1
        else:
            logging.info("Success. The partition was configured to {}".format(fs_type))

        return 0

    def mount_partition(self, partition, dest_dir):
        # return: 0 for success and -1 for fail
        os.system("sudo mkdir -p " + dest_dir)
        mount_cmd = "sudo mount " + partition.decode() + " " + dest_dir
        process = Popen(mount_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        line = process.stdout.readline()
        process.terminate()
        if not line:
            logging.info("Mount successfully!")
            logging.info("Mount partition {} to {} successfully".format(partition, dest_dir))
        else:
            logging.info("Mount failed: " + str(line))
            logging.error("Mount partition {} to {} failed, fail info: {}".format(partition, dest_dir, str(line)))
            return -1
        return 0

    def umount_partition(self, partition):
        # return: 0 for success and -1 for fail
        mount_cmd = "sudo umount " + partition.decode()
        process = Popen(mount_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        line = process.stdout.readline()
        process.terminate()
        if not line:
            logging.info("Unmount successfully!")
            logging.info("Umount partition {} successfully".format(partition))
        else:
            logging.error("Unmount failed: " + str(line))
            logging.error("Umount partition {} failed, fail info: {}".format(partition, str(line)))
            return -1
        return 0

    # get size and sector amount of the dut
    def get_dut_info(self, dut):
        list_cmd = "sudo fdisk -l " + dut
        process = Popen(list_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        while True:
            line = process.stdout.readline()
            tmp = re.match(b'Disk '+dut.encode("GBK")+b': ' + b'\d+.\d+\s*(GiB|TiB),\s*(\d+\s*)bytes,\s*(\d+)\s*sectors', line)
            #tmp_tb = re.match(b'Disk '+dut.encode("GBK")+b': '+b'\d+.\d+\s*TiB,\s*(\d+\s*)bytes,\s*(\d+)\s*sectors', line)
            if tmp != None:
                size_GB = int(int(tmp.group(2).decode())/1024/1024/1024)  # use bytes to get the size if more accurrent
                sector = int(tmp.group(3).decode())
                break
            if not line:
                size_GB = 0
                sector = 0
                break
        process.terminate()
        return size_GB, sector

    # get all partitions that created
    def get_partitions(self, dut):
        list_cmd = "sudo fdisk -l " + dut
        partition_list = []
        process = Popen(list_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
        while True:
            line = process.stdout.readline()
            tmp = re.match(b'('+dut.encode("GBK")+b'p\d+)\s*', line)
            if tmp != None:
                partition_list.append(tmp.group(1))
            if not line:
                break
        process.terminate()
        return partition_list

    def del_partition(self, dut):
        cmd = "sudo fdisk " + dut
        args = shlex.split(cmd)
        p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        p.stdin.write("d\n".encode("GBK"))
        p.stdin.write("\n".encode("GBK"))
        p.stdin.write("w\n".encode("GBK"))
        p.stdin.close()
        out = p.stdout.readlines()
        logging.debug('out of delete: {}'.format(out))
        p.terminate()

    def run_partition_filesystem(self, fs_conf, dut):
        case_name = fs_conf[0]
        logging.info("Start to run case: {}".format(case_name))

        primary_partition = fs_conf[1]
        logical_partition = fs_conf[2]
        fs_type = fs_conf[3]
        partition_amount = int(primary_partition) + int(logical_partition)
        size, sector = self.get_dut_info(dut)
        if size == 0:
            logging.error('get disk size failed')
            return -1
        logging.info("There're totally {} GB and {} sectors ".format(size, sector))
        if size > 2048: # DOS partition table format cannot be used on drives for volumes larger than 2048G
            size = 2047
            logging.info("use 2047G for partition test, due to DOS partition table format cannot be used on drives for volumes larger than 2048G")

        # size_of_partition = str(int(size)/partition_amount-1)  #split partition by size equally, in case of out of range in host level, -1
        size_of_partition = str(int(int(size)/partition_amount-1))
        ###########delete all partitions existed before testing################
        partition_list_ori = self.get_partitions(dut)
        logging.info('partition list before testing: '+str(partition_list_ori))
        if partition_list_ori:
            logging.info("There're existed partitions before testing: {}, delete them".format(partition_list_ori))
            # for i in range(1, len(partition_list_ori)+1):
            for partition in partition_list_ori:
                self.umount_partition(partition)
                self.del_partition(dut)

        ############create primary partitions######################
        if partition_amount == 1:  # if only 1 partition configured, set the size to default, i.e. full
            if self.create_partition(dut, 'p', '1', ' ') == -1:
                return -1
        else:
            for partition_number in range(1, int(primary_partition)+1):
                if self.create_partition(dut, 'p', str(partition_number), size_of_partition) == -1:
                    return -1

        ############create extended and logical partitions###################
        if int(logical_partition) > 0:
            if self.create_partition(dut, 'e', '4', ' ') == -1:  # allocate all the rest space to extened partition
                return -1
            for partition_number in range(1, int(logical_partition)+1):
                if self.create_partition(dut, 'l', str(partition_number), size_of_partition) == -1:
                    return -1

        ############config filesystem to every partition created in above steps and mount them seperately##############
        partition_list = self.get_partitions(dut)
        if partition_amount > 1 and (len(partition_list)) != partition_amount + 1:
            logging.info('#############partition list: '+str(partition_list))
            logging.info('################Some of the partitions created fail!####################')
            logging.error("Some of the partitions created fail!")
            return -1
        logging.info('partition list created: '+str(partition_list))
        # Sometimes partition created cannot be found by mkfs cmd. Let the kernel re-read the partition list.
        process = Popen('sudo partprobe', shell=True, stdout=PIPE, stderr=STDOUT)
        lines = process.stdout.readlines()

        logging.info('partprobe out: {}'.format(lines))
        time.sleep(3)
        logging.info("Partition list: {}".format(partition_list))
        process.terminate()
        if type(fs_type) is not tuple:
            for partition in partition_list:
                if partition != b'/dev/nvme0n1p4' and partition != b'/dev/sdb4':  # no need to configure extended partition
                    if self.config_fs(partition, fs_type) == -1:
                        return -1

                    dest_dir = "/media/fte" + partition.decode()
                    if self.mount_partition(partition, dest_dir) == -1:
                        return -1
        else:
            i = 0  # fs_type index
            for partition in partition_list:

                if partition != b'/dev/nvme0n1p4' and partition != b'/dev/sdb4':  # no need to configure extended partition, might be modified for sata device
                    if self.config_fs(partition, fs_type[i]) == -1:
                        return -1

                    dest_dir = "/media/fte" + partition.decode()
                    if self.mount_partition(partition, dest_dir) == -1:
                        return -1
                    i = i + 1
        logging.info("Start test teardown")
        for partition in partition_list:
            if partition != b'/dev/nvme0n1p4' and partition != b'/dev/sdb4':
                logging.info("Umount partition: {}".format(partition))
                if self.umount_partition(partition) == -1:
                    return -1
            # clear partition after testing
            logging.info("Delete partition: {}".format(partition))
            self.del_partition(dut)
        return 0

import pytest
import os
import sys
import subprocess
from subprocess import Popen, PIPE
import shlex
import time
import shutil
import glob
import filecmp
import logging
from datetime import datetime
from datetime import timedelta
izip = zip
filename = "./comparison.log"
fileobj = open(filename, "w")

device = " "
partition_1 = "partition_1"
partition_2 = "partition_2"
partition_list = [partition_1, partition_2]

size_1 = "30"
size_2 = "50"
size_list = [size_1, size_2]
flag = 0

partition1_source_folder = "/media/fte/" + partition_1 + "/1"
partition2_source_folder = "/media/fte/" + partition_2 + "/1"
partition1_target_folder = "/media/fte/" + partition_2 + "/2"
partition2_target_folder = "/media/fte/" + partition_1 + "/2"

source_folder_list = [partition1_source_folder, partition2_source_folder]
target_folder_list = [partition1_target_folder, partition2_target_folder]

@pytest.fixture(scope="class", params=["Kingston"])
def find_dev(request):
	print("-----Setup Start-----")
	
	disk_type = request.config.getoption("--device_type")
	
	if disk_type == "SATA":
		os.system("lsscsi > scsi.log")
		checkfile = open("scsi.log" , "r")	
		while True:
			keyword = checkfile.readline()
			print("request.config.getoption() is {}".format(request.config.getoption("--device_type")))
			print("request.param is {}".format(request.param))
			
			if request.param in keyword:
				tmp = keyword
				devname = tmp[53:61]
				print("device is {}".format(devname))
				break
		checkfile.close()	      
	elif disk_type == "NVMe":
		subprocess.check_call(["sudo","modprobe","nvme"]) 
		process = subprocess.Popen(["sudo","nvme","list"],stdout=subprocess.PIPE)
		out, err = process.communicate()
		if("no nvme devices" in str(out)):
			sys.exit("No nvme devices detected")
		else:
			devname = "/dev/nvme0n1"
	else:
		print("No device is found.")
		sys.exit()
	print("-----Setup End-----")
	
	print("-----Teardown Start-----")
	yield devname
	print("-----Teardown End-----")

def find_keyword(pattern, command):
	checkfile = open("fdisk.log", "r")
	while True:
		keyword = checkfile.readline()
		print("keyword: {}".format(keyword))
		if pattern in keyword:
			print("press command: {}".format(command))
			os.system(command)
			break      
	checkfile.close()

def create_partition(device, partition, size_of_partition):
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
	#cmd_out = p.stdout.read()
	#p.stdout.close()
	#print("cmd_out:{}".format(cmd_out))

def mount_partition(device, label):
	cmd = "sudo mkfs.ext4 " + device
	args = shlex.split(cmd)
	p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
	p.stdin.write("y\n".encode("GBK"))
	p.stdin.close()
	
	time.sleep(5)
	create_dirs = "sudo mkdir /media/fte/" + label
	os.system(create_dirs)
	mount_cmd = "sudo mount -t ext4 " + device + " /media/fte/" + label 
	os.system(mount_cmd)
	print("mount partition is done")

def change_permission(partition):
	cmd = "sudo chmod -R 777 /media/fte/" + partition
	os.system(cmd)
	print("permission setting is done.")

def copy_file_to_partition(partition):
	source_folder = "./1/"
	target_folder = "/media/fte/" + partition + "/1"
	shutil.copytree(source_folder, target_folder)

def copy_file_from_one_partition_to_another_partition(source_folder, target_folder):
	shutil.copytree(source_folder, target_folder)

def remove_all_files(partition):
	target_folder = "/media/fte/" + partition + "/2"
	print("target_folder is {}".format(target_folder))
	if os.path.exists(target_folder):
		shutil.rmtree(target_folder)

def compare_file(fileobj,source_folder, target_folder):
	comparison_flag = 0
	comparison = filecmp.dircmp(source_folder, target_folder)
	#comparison.report_full_closure()
	if len(comparison.diff_files) > 0:
		print("diff file is {}".format(comparison.diff_files))
		comparison_flag = 1
	if len(comparison.left_only) > 0:
		print("file left only is {}".format(comparison.left_only))
		comparison_flag = 2
	if len(comparison.right_only) > 0:
		print("file right only is {}".format(comparison.right_only))
		comparison_flag = 3
	if comparison_flag > 0: 
		fileobj.write(print_local_time() + "left folder is {}\r\n".format(source_folder))
		fileobj.write(print_local_time() + "right folder is {}\r\n".format(target_folder))
		fileobj.write(print_local_time() + "1 means diff file, 2 means left only and 3 means right only\r\n")
		fileobj.write(print_local_time() + "failed is {}\r\n".format(comparison_flag))
	return comparison_flag

def print_local_time():
	time = datetime.now().strftime("%Y-%m-%d %H:%M:%S ")
	return time

def run_small_file_comparison_test(fileobj, count):
	for partition, source_folder, target_folder in izip(partition_list, source_folder_list, target_folder_list):
		print("partition:{}, source_folder:{}, target_folder:{}".format(partition, source_folder, target_folder))
		copy_file_from_one_partition_to_another_partition(source_folder, target_folder)
		
		flag = compare_file(fileobj, source_folder, target_folder)	
		if flag > 0:
			break
		print("clean all folder")
		remove_all_files(partition)

	fileobj.write(print_local_time() + "count is {}\r\n".format(count))	
	return flag

class Test_small_file:
	@pytest.mark.testall
	@pytest.mark.createpartition
	def test_create_partition(self, find_dev, device_type):
		#check to see if SATA device is detected
		dev_partition_map = {}
		device = find_dev
		print("Found the device, and it is {}".format(device))
		if device == " ":
			print("device cannot be found")
			sys.exit()
		if device_type == "SATA":
			dev_partition_map[partition_1] = device + "1"
			dev_partition_map[partition_2] = device + "2"
		elif device_type == "NVMe":
			dev_partition_map[partition_1] = device + "p1"
			dev_partition_map[partition_2] = device + "p2"

		for num_partition, size_of_partition in izip(range(1,len(size_list) + 1), size_list):
			print("num_partition: {}, size_of_partition: {}".format(num_partition, size_of_partition))
			create_partition(device, str(num_partition), size_of_partition)
			time.sleep(5)
			
		for partition in dev_partition_map:
			print("partition:{}, value:{}".format(partition, dev_partition_map[partition]))
			mount_partition(dev_partition_map[partition], partition)
		
		for partition in dev_partition_map:
			change_permission(partition)
			copy_file_to_partition(partition)

	@pytest.mark.testall
	@pytest.mark.smallfile
	def test_small_file(self, test_runtime, test_loop):	
		# Check there is no log in "2" folder.
		count = 1
		wait_until = datetime.now() + timedelta(hours=int(test_runtime))
		for partition in partition_list:
			remove_all_files(partition)	
		
		start_time = datetime.now()
		if test_runtime == "0" or test_loop > "0":
			print("test loop mode.\r\n")
			fileobj.write(print_local_time() + "choosing the test loop mode.\r\n")
			for test_times in range(int(test_loop)):
				exit_flag = run_small_file_comparison_test(fileobj, count)
				if exit_flag > 0:
					break
				count += 1	
		else:		
			print("test runtime mode.\r\n")
			fileobj.write(print_local_time() + "choosing the test runtime mode.\r\n")
			while (wait_until > datetime.now()):
				exit_flag = run_small_file_comparison_test(fileobj, count)
				if exit_flag > 0:
					break
				count += 1	
		diff_time = datetime.now() - start_time
		fileobj.write(print_local_time() + "runtime spent {} seconds.\r\n".format(diff_time.seconds))
		fileobj.close()
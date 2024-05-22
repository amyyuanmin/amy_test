import pytest
import time
from datetime import datetime
import os
from datetime import datetime
import sfvs.click as click
from sfvs.device.device_factory import DeviceFactory
from sfvs.command.firmware.downfw_cmd import *
from subprocess import Popen, PIPE

def print_local_time(self = None):
    time=datetime.now().strftime('%Y-%m-%d_%H-%M-%S')     	
    return time

def check_device_url(url): #only a single string argument can be used if this is used for a type(below pytest_addoption) value as callback.
    """
    check the url is supported device type or not
    """
    device_types = DeviceFactory._device_types
    for dt in device_types:
        if url.find(dt) != -1:
            return url
    raise click.BadParameter('Device Url should be prefix with {}.'.format(*device_types))

def pytest_addoption(parser):
	parser.addoption("--T2_folder", required=True, dest="T2_folder", help="The T2 drive master test cases.")
	parser.addoption("--T3_folder", required=True, dest="T3_folder", help="The T3 drive master test cases.")
	parser.addoption("--sikuli_path", required=True, dest="sikuli_path", help="The T3 drive master test cases.")
	parser.addoption("--device", required=True, dest="device", type=check_device_url, help="uart device url.") #callback is replace by type or action
	parser.addoption("--token", dest="token", type=click.Path(exists=True), help="token file used to detoken contents.")
	parser.addoption("--fw_log", dest="fw_log", help="log file used to record fw log.")

def pytest_generate_tests(metafunc):
	# This is called for every test. Only get/set command line arguments
	# if the argument is specified in the list of test "fixturenames".
	T2_folder = metafunc.config.getoption("T2_folder")
	T3_folder = metafunc.config.getoption("T3_folder")
	sikuli_path = metafunc.config.getoption("sikuli_path")
	device = metafunc.config.getoption("device")
	token = metafunc.config.getoption("token")
	fw_log = metafunc.config.getoption("fw_log")

	if "T2_folder" in metafunc.fixturenames and T2_folder is not None:
		metafunc.parametrize("T2_folder", [T2_folder])
	if "T3_folder" in metafunc.fixturenames and T3_folder is not None:
		metafunc.parametrize("T3_folder", [T3_folder])
	if "sikuli_path" in metafunc.fixturenames and sikuli_path is not None:
		metafunc.parametrize("sikuli_path", [sikuli_path])
	if "device" in metafunc.fixturenames and device is not None:
		metafunc.parametrize("device", [device])
	if "token" in metafunc.fixturenames and token is not None:
		metafunc.parametrize("token", [token])
	if "fw_log" in metafunc.fixturenames and fw_log is not None:
		metafunc.parametrize("fw_log", [fw_log])
		
@pytest.fixture(scope="function", params= ["T2_folder", "T3_folder"])
def FindRecentFolder(request):
	if request.param == "T2_folder":
		if os.path.exists(os.path.join(os.getcwd(), "result.txt")):
			print("remove files")
			os.remove(os.path.join(os.getcwd(), "result.txt"))
		T2_folder = request.config.getoption("T2_folder")
		test_dir = T2_folder
	elif request.param == "T3_folder":
		T3_folder = request.config.getoption("T3_folder")
		test_dir = T3_folder
	lists = os.listdir(test_dir)  #List all folder in protocol directories and return the list.
	#print("test dir is {}".format(test_dir))
	lists.sort(key=lambda fn:os.path.getmtime(test_dir + '\\' + fn)) #According time to sort the element in lists.
	file_path = os.path.join(test_dir, lists[-1])
	return file_path	

def ListFilesInFolder(dir):
	if dir == "":
		print("folder empty")
		return None	
	lst = os.listdir(dir)
	print("List in the Folder -> {}".format(lst)) # list 
	print("Total file : {}".format(len(lst)))

	# del files/folder NOT *.log
	for tmp in lst:			
		if tmp.endswith(".log"):
			continue
		elif tmp.endswith(".Log"):
			continue
		else:
			lst.remove(tmp)
			print("Delete file -> {}".format(tmp))
	print("Total left file : {}".format(len(lst)))
	return lst

@pytest.fixture(scope="function")	
def CheckFolder(FindRecentFolder):
	global FolderFail
	FolderFail = 0
	fder_n = FindRecentFolder
	
	with open("result.txt", "a+") as log_record:
		log_record.writelines("\n\n.....Scanning the folder and check the results.\n" )
		if fder_n == "":
			print("\nfolder specified is NULL!!!, plz check it")
			log_record.writelines("\n\n.....folder specified is NULL!!!, plz check it \n" )	
		elif not os.path.exists(fder_n):
			print("\nfolder not exist!!!! plz check it")
			log_record.writelines("\n\n.....folder not exist!!!! plz check it: \n" + fder_n )			
		elif not os.listdir(fder_n):	
			print("\nNo log files in folder !!! plz check it")
			log_record.writelines("\n\n.....No log files in folder !!! plz check it: \n" + fder_n )				
		else:	
			print ("\n\n.....start check folder: " + fder_n)
			log_record.writelines("\n\n.....start check folder: " + fder_n)
			files_in_fder = ListFilesInFolder(fder_n)
			print("files_in_fder ->", files_in_fder)
			log_record.writelines("\n\nTotal Num: " + str(len(files_in_fder)) + "\r\n") 
			return files_in_fder

@pytest.fixture(scope="function")	
def CheckAllFiles(request, FindRecentFolder, CheckFolder):
	NumFail = 0
	path = FindRecentFolder
	files_in_fder = CheckFolder
	with open("result.txt", "a+") as log_record:
		for files in files_in_fder:
			fname = os.path.join(path, files)
			print("checking the filename ->", fname)
			with open(fname,'r') as fr:
				lines = fr.readlines()
				for index in range(0, len(lines)):
					if "total" in lines[index] or "No. Errors" in lines[index]:		# total # of errors.
						if "errors" in lines[index] or "Err" in lines[index]:
							find_total_of_errors = lines[index].find(":")		# To find error No.
							totaloferrors = lines[index][find_total_of_errors + 1 : -1]	
							NumofErrors = int(totaloferrors)
													
							if NumofErrors == 0:
								log_record.writelines(fname + "\r\n" + lines[index])
								log_record.writelines("pass\r\n")
								print("fname: ", fname)				
								print("pass")
								print("---------------------------------------------------------------------------------")								
							elif NumofErrors > 0 :
								NumFail += 1
								log_record.writelines(fname + "\r\n" + lines[index])
								log_record.writelines("\n==,FAIL==:\r\n")
								print("fname: ", fname)								
								print("==,FAIL==")
								break							
					
					elif "Error Information" in lines[index]:
						log_record.writelines(fname)
						log_record.writelines("\n==,FAIL==\r\n")
						print("fname: ", fname)
						print("==,FAIL==")
						NumFail += 1
						break
				
			## for SCT.log			
			if files == "SCT.log":
				sct_flag = 0
				with open(fname,'r') as fr:
					lines = fr.readlines()
					for index in range(0, len(lines)):
						if "++ FAIL:" in lines[index]:
							sct_flag = 1
							break
					log_record.writelines(fname)
					
					if sct_flag == 1:
						NumFail += 1
						log_record.writelines("\r\nSCT result : failed")					
						log_record.writelines("\r\n==FAIL==\r\n")
						print("\r\n==,FAIL==\r\n")							
					else:
						log_record.writelines("\r\nSCT result : passed")	
						log_record.writelines("\r\npass\r\n")
						print("\r\npass\r\n")	
		
		log_record.writelines("\r\nfailed cases: {}.\r\n".format(NumFail))
		print("\r\nfailed cases: {}.\r\n".format(NumFail))
		return (NumFail)

@pytest.fixture(scope="function")
def UART_Log(request):
    device = request.config.getoption("device")
    token = request.config.getoption("token")
    fw_log = request.config.getoption("fw_log")
    
    if not fw_log:
        fw_log = "fw_log.log"
    uart_device = DeviceFactory.create_device(device, msg_handler=LineMessageHandler())

    if uart_device is not None:
        #uart_device.user_name = "pi"
        #uart_device.password= "123456"
        uart_device.token = token
        uart_device.fw_log = fw_log
    
    if uart_device.open(device, token, fw_log, log_level = UartIO.DetokenLog(UartIO.LOG_LEVEL | UartIO.SYSTEM_TIMESTAMP)):
        uart_device.detoken = True
    else:
        pytest.fail()    
    
    yield fw_log
    uart_device.close()
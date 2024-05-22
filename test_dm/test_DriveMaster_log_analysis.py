import pytest
import os
import time
import shutil
import xml.etree.cElementTree as ET
import json

all_err = []
izip = zip

def generate_jsonfile(filename):
	data= {}
	testcase_name_list = []
	testcase_result_list = []
	testcaselist = []
	testsummary = {}	
	with open(filename, "r+") as filecheck:
		while True:
			testcase_result = ""
			testcase_name = ""
			line = filecheck.readline()
			if "total error case" in line:
				print(line)
				break
			if ".log" in line:
				line_list = line.split("\\")
				testcase_name = line_list[-1].strip()
				#print("testcase_name is {}".format(testcase_name))
				testcase_name_list.append(testcase_name)
			if "total # of" in line:
				line_list = line.split(":")
				testcase_result = line_list[-1].strip()
				#print("testcase_result is {}".format(testcase_result))
				if testcase_result == "1":
					testcase_result_list.append(-1)
				else:
					testcase_result_list.append(1)
			elif "SCT result" in line:
				line_list = line.split(":")
				testcase_result = line_list[-1].strip()
				#print("testcase_result is {}".format(testcase_result))
				if testcase_result == "failed":
					testcase_result_list.append(-1)
				else:
					testcase_result_list.append(1)
	#print("testname is {}".format(testcase_name_list))
	#print("result is {}".format(testcase_result_list))
	#print("*********************************************************")
	for testname, testresult in izip(testcase_name_list, testcase_result_list):
		#print("testname is {}".format(testname))
		#print("result is {}".format(testresult))
		if testresult != -1:
			data[testname] = "Pass"
		else:
			data[testname] = "Fail"

		#print("data[testname] is {}".format(data[testname]))
		#print("------------------------------------------------------")
		testcaselist.append(testname)	
	#print("data is {}".format(data))
	
	testsummary["Tool"] = "DriveMaster"
	testsummary["TestCaseSummary"] = data
	
	with open("result_json.json", 'w') as jsonfile:
		json.dump(testsummary, jsonfile)
	return testcaselist

def xml_format_summary(input_file, testcaselist, output_file):

	root = ET.Element("TestCaseSummary")
	with open(input_file, "r") as data_file:
		data_item = json.load(data_file)

	tool = data_item['Tool']
	tool_name = ET.Element("Tool")
	tool_name.text = tool
	root.append(tool_name)

	# Add testcase, testresult.
	final_result = "Pass"
	for testcase in testcaselist:
		testresult = data_item['TestCaseSummary'][testcase]
		#print("test case is {}".format(testcase))
		#print("test result is {}".format(testresult))
		if testresult == "Fail": 
			final_result = testresult
			break

	FinalResult = ET.Element("FinalResult")
	FinalResult.text = final_result
	root.append(FinalResult)

	for testcase in testcaselist:
		testcasename = testcase
		TestCaseName = ET.SubElement(FinalResult, "TestCaseName")
		TestCaseName.text = testcasename
		
		testresult = data_item['TestCaseSummary'][testcase]
		TestResult = ET.SubElement(FinalResult, "TestResult")
		TestResult.text = testresult

	tree = ET.ElementTree(root)
	with open(output_file, "wb") as fh:
		tree.write(fh, encoding = "utf-8")

class Test_DriveMaster_log_analysis:
	def test_run_dm_testcase(self, UART_Log, request):
		sikuli_path = request.config.getoption("sikuli_path")
		T2_folder = request.config.getoption("T2_folder")
		T3_folder = request.config.getoption("T3_folder")
		
		os.system("runsikulix.cmd -r " + sikuli_path + " --args " + T2_folder + " " + T3_folder)
		
	def test_check_dm_log(self, CheckAllFiles):		
		error = CheckAllFiles
		all_err.append(error)
		
		if (len(all_err) == 2):
			NumFail = sum(all_err)	
			with open("result.txt", "a+") as log_record:
				log_record.writelines("total error case is {}".format(NumFail))
				print("total error case is {}".format(NumFail))

	def test_generate_xml_json_summary(self):
		testcaselist = generate_jsonfile("result.txt")	
		xml_format_summary("result_json.json", testcaselist, "result_xml.xml")
		
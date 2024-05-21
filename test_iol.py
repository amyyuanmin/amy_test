#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2081 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2018 Marvell Semiconductor.
#
# Version Control Information:
#
#  $Id$
#  revision: 0.1
#
#  Author:  YuanMin
#
#  May 20, 2019
#####################################################################################################################
 
#import IOL_cmd_parser
 
import subprocess
import json
import xml.etree.cElementTree as ET
import pytest
import os
import shlex
from configparser import ConfigParser
import time
import re, sys
import shutil
import logging

logging.basicConfig(level=logging.DEBUG)
mylogger = logging.getLogger()

def copy_cfg_from_local_to_server(local_log, cfg):
    cmd = "sshpass -p 123456 scp  -r -o StrictHostKeyChecking=no  {} {}".format(local_log, cfg)
    print(cmd)
    result=os.system(cmd)
    if result:
        pytest.fail("copy server cfg file to local is failed.")
    else:
        print("copy server cfg file is success")      
        
def get_cfg(config_file):
    config = ConfigParser()
    config.read(config_file)
    iol_version= config.get("IOL", "iol_version")
    print(iol_version)
    server_folder=config.get("IOL", "server_folder")
    cmd="cat /etc/hostname"
    result=os.popen(cmd)
    hostname=result.read().strip()
    print(hostname)
    iol="/home/"+hostname+"/"+iol_version+"/nvme/manage"
    print (iol)
    return iol,server_folder
    
def find_host():
    cmd="cat /etc/hostname"
    result=os.popen(cmd)
    host_name=result.read().strip()
    print("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name
    
def run_iol_script(path, result, script, logDir):    
    flag = 0
    testAttempts = 0
    testFails = 0

    testcaselist = []
    data= {}
    testsummary = {} 

    iol_case = "./runtest.sh"

    with open(path + result, 'a+') as f_sum:
        test = shlex.split(script)
        if iol_case in test:
            testcase = "IOL_test_" + test[2].split("=")[-1].replace(":",".")
        else:
            testcase = None

        try:
            testAttempts += 1
            failedCount = "0"
           
            process = subprocess.Popen(' '.join(test), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            
            with open(path+"/log", 'w+') as log:
                while True:                    
                    line = process.stdout.readline()
                    if not line:
                        break

                    line = str(line)
#                    print ("line: {}".format(line))					
                    if re.search(r"failed"" +"":",line):                
                        mylogger.info("failed line is: {}".format(line))
                    
                        failedCount = line.strip().split(":")[-1]
                        failedCount = re.sub("\D", "",failedCount)
                        mylogger.info("failed count is: {}".format(failedCount))
                        log.write(line.strip()+"\n")
         
            if failedCount != "0":              
                raise subprocess.CalledProcessError(None,"Test Failed")
            flag = 0    
            save_log(path,test,f_sum,"Pass",logDir)     
            data[testcase] = "Pass"
        except subprocess.CalledProcessError as e:
            testFails += 1 
            flag = -1
            save_log(path, test, f_sum, "Fail", logDir) 
            data[testcase] = "Fail"

        testcaselist.append(testcase)  
            #break
        sys.stdout.flush()        
        mylogger.info("Out of {} Tests. There were {} Failures".format(testAttempts,testFails))
        return flag
  

def save_log(path,test,f_summary,pattern,logDir):
    #save the IOL test log to IOL_log folder
    logCount = str(len(os.listdir(logDir))+1)+"_"
    logFile = os.path.join(logDir,logCount+"IOL_log"+test[2].split("=")[-1].replace(":","."))
    
    if ("tnvme" in test[1]):
        print (test[1])
        subprocess.check_call(["cp",path+"/log",logFile])          
    else:
        print(test[1])
        subprocess.check_call(["cp","Logs/log0",logFile]) #store logs for failed test

    print ("IOL Test %-10s:%-30s" %( test[2].split("=")[-1],pattern))
    
    f_summary.write("IOL Test %-10s:%-30s\n"% (test[2].split("=")[-1],pattern)) 
   
    
def log_summary(path,result,summary):
    #parse IOL summary  log
    flag=0
    with open(path+summary,'w+',errors='ignore') as summary:
        with open(path+result.strip('\n'),'r',errors='ignore') as fi:
            lineNo=0
            linecount=len(fi.readlines()) 
    
        
        with open(path+result.strip('\n'),errors='ignore') as f:
            while True:
                line=f.readline()
                lineNo += 1
                if "Fail" in line:
                    print ("Found FAIL case in IOL:",line)
                    summary.write("IOL Test :Fail\n" )
                    pytest.fail("iol test failed!")
                if (linecount == lineNo):
                    if "Pass" in line:
                        print ("All case in IOL is PASS")
                        summary.write("IOL Test :Pass\n" ) 
                if not line:
                     break
     

    
def load_dnvme_driver():
    
    #remove nvme driver, then Load dnvme driver. fail if cannot load
    subprocess.call(["sudo","rmmod","nvme"]) #remove nvme. fail if cannot load
    subprocess.call(["sudo","rmmod","nvme_core"]) #remove nvme. fail if cannot load
    time.sleep(5) # sometimes takes a little bit to enumerate
    subprocess.call(["pwd"]) #remove nvme. fail if cannot load
    subprocess.call(["sudo","insmod","./../dnvme/dnvme.ko"]) #remove nvme. fail if cannot load
    proc = subprocess.Popen(["ls","/dev/nvme0"],stdout=subprocess.PIPE,stderr=subprocess.PIPE) # check if dut exists
    out,err = proc.communicate()
    if(err != b''):
        sys.exit("/dev/nvme0 is missing. Test exiting")

def load_nvme_driver():
    #remove nvme driver, then Load dnvme driver. fail if cannot load
    subprocess.call(["sudo","rmmod","dnvme"]) #remove dnvme. fail if cannot load
   
    subprocess.call(["sudo","modprobe","nvme"]) #insmod nvme. f
    proc = subprocess.Popen(["ls","/dev/nvme0"],stdout=subprocess.PIPE,stderr=subprocess.PIPE) # check if dut exists
    out,err = proc.communicate()
    if(err != b''):
        sys.exit("/dev/nvme0 is missing. Test exiting")
        

def sortout_summary(IOL,logDir,filePath):
    
    subprocess.call(["sudo","mv", filePath+"/summary.log", IOL])
    subprocess.call(["sudo","mv", filePath+"/iol_result.log", IOL])
    #subprocess.call(["sudo","mv", filePath+"/iol_summary.xml", IOL])    
    #subprocess.call(["sudo","mv", filePath+"/iol_summary.json", IOL])


def xml_format_summary(input_file, testcaselist, output_file):
    ### create xml type summary
    ### input: fio result log file, pattern for fio test pass criteria, and json summary filename.
    ### output: fio testcase list for xml used.

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



def pytest_generate_tests(metafunc):
 
    if 'case' in metafunc.fixturenames:
        script = metafunc.config.option.case

        with open(script) as testList:
            while True: #detect and skip comments
                pos = testList.tell()
                line = testList.readline()
                #print (line)
                if line[0] != "#":#if not comment
                    testList.seek(pos)#take read cursor back to non comment line
                    break
            version = testList.readline().strip().split("=")[1] 
            device = testList.readline().strip().split("=")[1]
            print("The version is %s, device is %s" % (version,device))  
            #parse IOL output file      
            testcaselist = []
            data= {}
            testsummary = {}         
            case=[]
            print (testList)
            for test in testList:
                if(not test.strip()):#skip any lines that are just spaces and newlines
                    continue
                if (test.startswith("#")):
                    continue
                test = test.replace('"$device"',device).replace('"$version"',version) #split the runtnvme command to extract some data             
                #print (test)
                case.append(test.strip('\n'))
                #print(case)     
        #print (case)
        metafunc.parametrize("case", case)


class TestIOL():
    global uart_device
    global IOL,logDir,fs
    uart_device = None

    
    @pytest.fixture(scope="module", autouse=True)
    def setup(self):
        #print (request.param)
        global IOL, iol,filePath,logDir,server_folder,fs,flag
        flag=0
        cfg_file="./iol_cfg.txt"
        iol,server_folder=get_cfg(cfg_file)
        print(iol)      
        print("------------------------------Setup start------------------------------") 
        filePath = os.path.dirname(os.path.realpath(__file__))

        #start testing
        print("iol_interact dir: {}".format(iol))
        filePath = os.path.dirname(os.path.realpath(__file__))
        print("filepath dir: {}".format(filePath))
        #subprocess.call(["cp",os.path.join(filePath,scriptName),iol]) #take test cases script to where iolinteract is
        now = time.strftime('[%Y-%m-%d %H:%M:%S] ',time.localtime(time.time()))
        prtstr = '{0}start IOL test.'.format(now)   
        print(prtstr)
        hostname=find_host()
        report = hostname + "_iol_test_result.xml"
        if os.path.exists(report):
            print ("remove IOL result")
            os.remove(report)
			
        IOL = os.path.join(os.path.dirname(os.path.realpath(__file__)),hostname+"_IOL_Logs")
        #shutil.rmtree(IOL)
        logDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),hostname+"_IOL_Logs/IOL_summary")
        if os.path.exists(IOL):
            shutil.rmtree(IOL)
  
        if not os.path.exists(IOL): #create dir for logs
            os.makedirs(IOL) 
        if not os.path.exists(logDir): #create dir for logs
            os.makedirs(logDir)
                
        os.chdir(iol) #change working directory to iolinteract location   
     
      
#        load_dnvme_driver()
        print("------------------------------Setup end------------------------------")
        yield
        sortout_summary(IOL,logDir,filePath)
        print(server_folder)
        #fsname="cd15\20190518_1703_03_iol"
        print(fs)
        server_cfg=server_folder+"/"+ fs    
        #result=copy_cfg_from_local_to_server(IOL, server_cfg)
        #if result !=1:
            #shutil.rmtree(IOL)
        load_nvme_driver() 
        #subprocess.call(["sudo","mv", filePath+"/fw_log.log", IOL])
        print("-----------------Teardown() end-----------------")


    @pytest.mark.timeout(timeout=300,method="signal")   
    def test_iol(self,fsname,case,setup):
        iol_result="/iol_result.log"
        iol_summary="/summary.log"     
        global IOL, iol,filePath,logDir,fs,flag
        fs=fsname
#        print(case)
        if flag == -1:
            pytest.exit('Fio test failed!')

        flag = run_iol_script(filePath, iol_result, case, logDir)
        log_summary(filePath,iol_result,iol_summary)      
        
        #sys.exit(testFails)
        #print ("IOL finish...")    
        now = time.strftime('[%Y-%m-%d %H:%M:%S] ',time.localtime(time.time()))
        prtstr = '{0}complete.'.format(now)
        print(prtstr)
        #sortout_summary(IOL,logDir,filePath)
                #sys.stdout.flush() 
                #uart.dev_write('info')
                #assert uart.wait_keyword('Finished: info', 60) == 0, "Fail in info cmd."
"""
        finally:   
        sortout_summary(IOL,logDir,filePath)
        print(server_folder)
        print(fsname)
        server_cfg=server_folder+"/"+ fsname
        #sshpass -p 123456 scp -r /home/cd15/WP_TEST/target_script/iol/IOL_Logs/ svt@10.25.130.97:/home/kk/logs/CI_Test/cd15/20190518_1703_03_iol

        copy_cfg_from_local_to_server(IOL, server_cfg)

#cfg = '"/home/kk/logs/CI_Test"/cd15/cd15/20190518_1703_03_iol'
"""
        #except RuntimeError as e:
            #print("Generate runtime error:{}".format(e.args[0]))
if __name__ == "__main__":
    main()

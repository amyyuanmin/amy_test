#!/usr/bin/python
import pytest
from configparser import ConfigParser
import os
import subprocess
import shutil
import re
import time
import logging

logging.basicConfig(level=logging.DEBUG)
mylogger = logging.getLogger()

cfg_file="./fio_cfg.txt"
class CaseGenerator():
    def get_case_fio(self, list_all, key):
        '''
        get cotent for each part seperated by []
        the configure file should contain a [global] part at the beginning
        ''' 
        case_all=[]
        list_tmp=[]
        flag=0
        for el in list_all:
            if key not in el and el != '\n':
                list_tmp.append("--"+el.strip('\n')) #store option in a list with -- added before
                continue
            elif key in el and flag==0: #for first section, i.e. global in fio, just option added, no need for the [global] mark
                flag=flag+1
                continue
            elif key in el and flag!=0:
                case_all.append(list_tmp)
                list_tmp=[el.strip('\n').strip('[]')]  #content in [] as case name
                continue
        case_all.append(list_tmp)
        return case_all
    
    
    def generate_case_fio(self, filename):
        '''
        generate option list for each case by combining global and specific part
        the case name is the first element of each list
        ''' 
        file = open(filename, 'r')
        list_all=[]    
    
        for line in file:
            list_all.append(line)    
        file.close()
        case_all = self.get_case_fio(list_all, '[') #for fio, [] used for each configure
        opt_list = []
        opt_tmp = []
    
        for i in range(len(case_all)):
            if i > 0:
                opt_tmp.append(case_all[i][0])  #first element for case name
                opt_tmp.extend(case_all[0])  #option in global part
                opt_tmp.extend(case_all[i][1:])  #option in each case
                opt_list.append(opt_tmp)  
                opt_tmp=[]
        return opt_list    

def get_cfg(config_file, caseSuite):
    '''
    get the config file for specific test suite from the global config file.
    config_file: "./fio_cfg.txt", fixed in this script (at the top)
    caseSuite: test suite: precommit, postcommit or nightly
    return: configFile from fio config, timeout of each fio test case
    '''
    config = ConfigParser()
    config.read(config_file)
    #log= config.get("Fio", "log")
    configFile = config.get("Fio", caseSuite)
    timeout = config.get('Fio', caseSuite+'_timeout')
    
    return configFile, timeout
    
def find_host():
    cmd="cat /etc/hostname"
    result=os.popen(cmd)
    host_name=result.read().strip()
    print("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name

    
def pytest_generate_tests(metafunc):  
    '''
    pytest build-in hook, used to parametrize the fio configure file to a list for loop run
    '''
    idlist = []
    argvalues = []    
    case = metafunc.config.getoption('caseSuite')
    configFile, timeout = get_cfg(cfg_file, case)
    cg = CaseGenerator()
    config_list = cg.generate_case_fio(configFile)  #para for getoption is the dest of each addoption
    
    for case in config_list:
        idlist.append(case[0])
        argvalues.append(case[0:]) #also pass the first element which is the case id to test function, used for log
    metafunc.parametrize('fio_config', argvalues, ids=idlist) #ids for case id
    metafunc.parametrize('timeout', [timeout]) #ids for case id

class TestFio():
    @pytest.fixture(scope='class')
    def log_folder(self):
        '''
        setup for the whole class: clear former logs and create new folder for logs
        '''
        global flag #flag used to check if the last test failed
        flag=0    
        hostname=find_host()
        report = hostname + "_fio_test_result.xml"
        if os.path.exists(report):
            os.remove(report)

        folder_name = hostname+"_FIO_logs"
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        yield log_folder
        
    @pytest.fixture(scope='function')
    def log(self, log_folder, fio_config):
        '''
        setup for each test, runtime log with case name
        '''            
        fio_logname = "fio_"+str(fio_config[0])+".log" #case name is the first element of fio_config
        fio_log = log_folder + '/' + fio_logname
        yield fio_log
        #subprocess.check_call(["mv",os.path.join(os.getcwd(), fio_logname), log_temp_folder])
            

    def test_fio(self, log, fio_config, timeout):
        '''
        Main body of the fio test
        Para:
        log: the setup function to get the fio log
        fio_config: fio config got from config file
        '''
        global flag
        if flag == -1:
            mylogger.info(" FIO test check is failed.")
            pytest.exit('Fio test failed!')
        
        job = '--name '+fio_config[0]
        option = " ".join(fio_config[1:])
        cmd = "sudo fio {0} {1} --output={2}".format(job, option, log)
        print(cmd)
        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True) 
        t_beginning = time.time()
        seconds_passed = 0 
        while True:
            if p.poll() is not None: 
                mylogger.info(" FIO test is done.")
                break 
            time.sleep(1)
            seconds_passed = time.time() - t_beginning 
            if seconds_passed > int(timeout): 
                p.terminate() 
                flag = -1
                mylogger.info(" FIO test is failed due to timeout.")
                pytest.fail('Failed due to timeout')
        result = self.check_result(log, 'err=')
        if result != 'Pass':
            flag = -1
            mylogger.info(" FIO test is failed.")
            pytest.fail('Fio test failed!') 
        

    def check_result(self, log_file, pattern):
        result = 'Pass'
        with open(log_file,'r') as processLog:
            while True:  
                entry = processLog.readline()
                if pattern in entry:
                    if pattern + " 0" in entry:
                        result = "Pass"
                        break
                    else:
                        result = "Fail"
                        break
                elif entry == '':
                    break
            return result

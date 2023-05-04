#!/usr/bin/python
import pytest
from configparser import ConfigParser
import os
import subprocess
import shutil
import re
import time
import logging
import glob
import threading
from datetime import datetime
import inspect
import ctypes

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
cfg_file = "./fio_cfg.txt"


class CaseGenerator():
    def get_case_fio(self, list_all, key):
        '''
        get cotent for each part seperated by []
        the configure file should contain a [global] part at the beginning
        '''
        case_all = []
        list_tmp = []
        global flag
        flag = 0
        for el in list_all:
            if key not in el and el != '\n':
                list_tmp.append("--"+el.strip('\n'))  # store option in a list with -- added before
                continue
            # for first section, i.e. global in fio, just option added, no need for the [global] mark
            elif key in el and flag == 0:
                flag = flag+1
                continue
            elif key in el and flag != 0:
                case_all.append(list_tmp)
                list_tmp = [el.strip('\n').strip('[]')]  # content in [] as case name
                continue
        case_all.append(list_tmp)
        return case_all

    def generate_case_fio(self, filename):
        '''
        generate option list for each case by combining global and specific part
        the case name is the first element of each list
        '''
        file = open(filename, 'r')
        list_all = []

        for line in file:
            list_all.append(line)
        file.close()
        case_all = self.get_case_fio(list_all, '[')  # for fio, [] used for each configure
        opt_list = []
        opt_tmp = []

        for i in range(len(case_all)):
            if i > 0:
                opt_tmp.append(case_all[i][0])  # first element for case name
                opt_tmp.extend(case_all[0])  # option in global part
                opt_tmp.extend(case_all[i][1:])  # option in each case
                opt_list.append(opt_tmp)
                opt_tmp = []
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
    cmd = "cat /etc/hostname"
    result = os.popen(cmd)
    host_name = result.read().strip()
    logging.info("host_name at testbed is {}".format(host_name))
    result.close()
    return host_name


def pytest_generate_tests(metafunc):
    '''
    pytest build-in hook, used to parametrize the fio configure file to a list for loop run
    '''
    idlist = []
    argvalues = []
    case = metafunc.config.getoption('caseSuite')
    logging.info(case)
    configFile, timeout = get_cfg(cfg_file, case)
    cg = CaseGenerator()
    config_list = cg.generate_case_fio(configFile)  # para for getoption is the dest of each addoption

    for case in config_list:
        idlist.append(case[0])
        argvalues.append(case[0:])  # also pass the first element which is the case id to test function, used for log
    metafunc.parametrize('fio_config', argvalues, ids=idlist)  # ids for case id
    metafunc.parametrize('timeout', [timeout])  # ids for case id


def link_speed_change(interval, loop, dev, logfile):
    global fio_flag, flag
    logging.info("link speed change loop is {}".format(loop))
    logging.info("link speed change interval time is " '%.2f' % float(interval))
    log = logfile + '/link_speed.log'
    logging.info(log)
    logging.info("----start loop change link speed---")

    for cycle in range(1, int(loop)+1):
        cmd = "sudo fdisk -l | grep -w nvme0n1"
        result = os.popen(cmd)
        out = result.read().strip()
        result.close()
        if not ("/dev/nvme0n1" in str(out)):
            logging.error("-------------Cannot find the nvme disk, exit the link speed test-----------")
            fio_flag = -1
            flag = -1
            break

        if fio_flag == 0:
            logging.info("fio test is done, exit link speed change thread")
            break
        if fio_flag == -1:
            logging.error("fio have error monitor AER error,,exit link speed change thread")
            break
        with open(log, 'a+') as f:
            f.write('find nvme device:'+str(out)+'\n')
            f.write('Test loop:'+str(cycle)+'\n')
            loop_time = datetime.now()
            f.write('time:'+str(loop_time)+'\n')

        for i in range(1, 6): #change link speed GEN1~GEN5
            setpci_cmd = "sh ./change_link_speed.sh "+dev+" "+str(i)+" "+log
            if "60" in interval:
                logging.info(setpci_cmd)
            p = subprocess.Popen(setpci_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
            time.sleep(float(interval))


def find_marvell_pci():
    cmd = "lspci | grep Marvell |awk -F ' ' '{print $1}'"
    p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    pci = p.stdout.read()
    return pci.decode()


def enalbe_aer(dev):
    logging.info("enalbe the AER register")
    cmd1 = "setpci -s 0000:"+dev+" ECAP_AER+0x14.L"
    logging.info("read ECAP_AER_0x14 before setting:"+cmd1)
    p = subprocess.Popen(cmd1, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    logging.info(p.stdout.read())
    cmd2 = "setpci -s 0000:"+dev+" ECAP_AER+0x14.L=0xFFFFFFFF"
    logging.info(cmd2)
    p = subprocess.Popen(cmd2, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    time.sleep(1)
    p = subprocess.Popen(cmd1, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    logging.info("read ECAP_AER_0x14 after setting:")
    logging.info(p.stdout.read())
    cmd3 = "setpci -s 0000:"+dev + " ECAP_AER+0x08.L"
    logging.info("read ECAP_AER_0x08 before setting:"+cmd3)
    p = subprocess.Popen(cmd3, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    logging.info(p.stdout.read())
    cmd4 = "setpci -s 0000:"+dev+" ECAP_AER+0x08.L=0xFFFFFFFF"
    logging.info(cmd4)
    p = subprocess.Popen(cmd4, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    time.sleep(1)
    p = subprocess.Popen(cmd3, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    logging.info("read ECAP_AER_0x08 after setting:")
    logging.info(p.stdout.read())
    logging.info("----enalbe the AER register done----")


def monitor_aer(dev, logfile):
    global fio_flag, flag
    enalbe_aer(dev)
    logging.info("----------monitor PCIE AER-----------")
    log = logfile + '/dmesg.log'
    dmesg_clean = "sudo dmesg -c"
    logging.info(dmesg_clean)
    os.system(dmesg_clean)
    time.sleep(2)
    dmesg_cmd = "sudo dmesg -w > "+log + "&"
    logging.info(dmesg_cmd)
    os.system(dmesg_cmd)
    with open(log, 'a+') as f:
        while True:
            line = f.readline()
            if "AER" in line:
                logging.error("find AER error{}".format(line))
                # if "Uncorrected (Fatal)" in line:
                #logging.info("find fatal AER error{}".format(line))
                os.system("sudo killall dmesg")
                fio_flag = -1
                flag = -1
                break
            if fio_flag == 0:
                logging.info("fio test is done, exit AER monitor thread")
                logging.info("kill dmesg")
                os.system("sudo killall dmesg")
                break
            if fio_flag == -1:
                logging.error("fio have error or monitor AER error, exit AER monitor thread")
                os.system("sudo killall dmesg")
                break


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")


class Thread(threading.Thread):
    def _get_my_tid(self):
        """determines this (self's) thread id"""
        if not self.isAlive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self.ident

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise AssertionError("could not determine the thread's id")

    def raise_exc(self, exctype):
        """raises the given exception type in the context of this thread"""
        _async_raise(self._get_my_tid(), exctype)

    def terminate(self):
        """raises SystemExit in the context of the given thread, which should 
        cause the thread to exit silently (unless caught)"""
        self.raise_exc(SystemExit)


class TestFio():
    @pytest.fixture(scope='class')
    def log_folder(self, get_parameter):
        '''
        setup for the whole class: clear former logs and create new folder for logs
        '''
        global flag, fio_flag  # flag used to check if the last test failed
        loop, interval = get_parameter
        flag = 0
        fio_flag = 2
        hostname = find_host()
        folder_name = hostname + "_link_speed_logs"
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        pci = find_marvell_pci().strip()
        logging.info("marvell pcie id is {}".format(pci))
        #t1= Thread(target=monitor_aer,args=(pci,log,fio_flag))
        #t2= Thread(target=link_speed_change,args=(interval,loop,pci,log,fio_flag))
        logging.info(log_folder)
        logging.info("---")
        t1 = threading.Thread(target=monitor_aer, args=(pci, log_folder))
        t2 = threading.Thread(target=link_speed_change, args=(interval, loop, pci, log_folder))
        t1.start()
        time.sleep(10)
        t2.start()

        yield log_folder
        logging.info(flag)
        fio_flag = flag
        logging.info("fio_flag is:{}".format(fio_flag))
        t2.join()
        # t1.terminate()
        t1.join()

        expected = glob.glob('*.expected')
        received = glob.glob('*.received')
        if expected:
            for ext in expected:
                os.system('mv {} {}'.format(ext, log_folder))
        if received:
            for recv in received:
                os.system('mv {} {}'.format(recv, log_folder))

    @pytest.fixture(scope='function')
    def log(self, log_folder, fio_config):
        '''
        setup for each test, runtime log with case name
        '''

        fio_logname = "fio_" + str(fio_config[0]) + ".log"  # case name is the first element of fio_config
        fio_log = log_folder + '/' + fio_logname
        yield fio_log

    @pytest.fixture(scope='class')
    def result_summary(self, log_folder):
        '''
        Create a summary log for fio test cases
        '''
        summary_file = log_folder + '/Link_Speed_Dynamic_Change_result.log'
        yield summary_file

    def test_fio(self, log, fio_config, timeout, result_summary):
        '''
        Main body of the fio test
        Para:
        log: the setup function to get the fio log
        fio_config: fio config got from config file
        '''
        global flag, fio_flag
        if flag == -1:
            logging.error("FIO test failed.")
            pytest.exit('Fio test failed!')
        job = '--name '+fio_config[0]
        option = " ".join(fio_config[1:])

        cmd = "sudo fio {0} {1} --output={2}".format(job, option, log)
        logging.info(cmd)

        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        t_beginning = time.time()
        seconds_passed = 0
        while True:
            if p.poll() is not None:
                logging.info(" FIO test is done.")
                break
            time.sleep(1)
            seconds_passed = time.time() - t_beginning
            if fio_flag == -1:
                logging.error(" FIO test is failed due to monitor AER error")
                with open(result_summary, 'a+') as f:
                    f.write('%-25s----%-35s\n' % (fio_config[0], 'Fail'))
                pytest.fail('Failed due to monitor fatal AER error.')
            if seconds_passed > int(timeout):
                p.terminate()
                flag = -1
                logging.error(" FIO test is failed due to timeout.")
                with open(result_summary, 'a+') as f:
                    f.write('%-25s----%-35s\n' % (fio_config[0], 'Fail'))
                pytest.fail('Failed due to timeout')

        if flag == -1:
            fio_flag = flag
            logging.info("fio_flag is:{}".format(fio_flag))

        result = self.check_result(log, 'err=')

        with open(result_summary, 'a+') as f:
            f.write('%-25s----%-35s\n' % (fio_config[0], result))

        if result != 'Pass':
            flag = -1
            logging.error(" FIO test is failed.")
            pytest.fail('Fio test failed!')

    def check_result(self, log_file, pattern):
        result = 'Pass'
        with open(log_file, 'r') as processLog:
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

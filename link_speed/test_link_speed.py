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


def get_cfg(config_file, caseSuite):
    '''
    get the config file for specific test suite from the global config file.
    config_file: "./fio_cfg.txt", fixed in this script (at the top)
    caseSuite: test suite: precommit, postcommit or nightly
    return: configFile from fio config, timeout of each fio test case
    '''
    config = ConfigParser()
    config.read(config_file)
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


def link_speed_change(interval, loop, dev, logfile):
    global flag
    logging.info("link speed change loop is {}".format(loop))
    logging.info("link speed change interval time is " '%.2f' % float(interval))
    log = os.path.abspath(os.path.dirname(logfile)) + '/link_speed.log'
    logging.info(log)
    logging.info("----start loop change link speed---")

    for cycle in range(1, int(loop)+1):
        cmd = "sudo fdisk -l | grep -w nvme0n1"
        result = os.popen(cmd)
        out = result.read().strip()
        result.close()
        if not ("/dev/nvme0n1" in str(out)):
            logging.error("-------------Cannot find the nvme disk, exit the link speed test-----------")
            flag = -1

        if flag == -1:
            logging.error("monitor error,exit link speed change thread")
            return -1
        with open(log, 'a+') as f:
            f.write('find nvme device:'+str(out)+'\n')
            f.write('Test loop:'+str(cycle)+'\n')
            loop_time = datetime.now()
            f.write('time:'+str(loop_time)+'\n')

        for i in range(1, 6):  #change link speed GEN1~GEN5
            setpci_cmd = "sh ./change_link_speed.sh "+dev+" "+str(i)+" "+log
            if "60" in interval:
                logging.info(setpci_cmd)
            p = subprocess.Popen(setpci_cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
            time.sleep(float(interval))
    logging.info("link speed test is done")
    flag = 0
    return flag


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
    global flag
    enalbe_aer(dev)
    logging.info("----------monitor PCIE AER-----------")
    log = os.path.abspath(os.path.dirname(logfile)) + '/dmesg.log'
    dmesg_clean = "sudo dmesg -c"
    logging.info(dmesg_clean)
    os.system(dmesg_clean)
    time.sleep(2)
    dmesg_cmd = "sudo dmesg -w > " + log + "&"
    logging.info(dmesg_cmd)
    os.system(dmesg_cmd)
    with open(log, 'a+') as f:
        while True:
            line = f.readline()
            if "AER" in line:
                logging.error("find AER error{}".format(line))
                os.system("sudo killall dmesg")
                flag = -1
                break
            if flag == 0:
                logging.info("link speed change test is done, exit AER monitor thread")
                logging.info("kill dmesg")
                os.system("sudo killall dmesg")
                break
            if flag == -1:
                logging.error("link speed change test have error, exit AER monitor thread")
                os.system("sudo killall dmesg")
                break


class Testlinkspeed():
    @pytest.fixture(scope='class')
    def log_folder(self):
        '''
        setup for the whole class: clear former logs and create new folder for logs
        '''
        global flag  # flag used to check if the last test failed

        hostname = find_host()
        folder_name = hostname+"_link_speed_logs"
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)

        yield log_folder
        expected = glob.glob('*.expected')
        received = glob.glob('*.received')
        if expected:
            for ext in expected:
                os.system('mv {} {}'.format(ext, log_folder))
        if received:
            for recv in received:
                os.system('mv {} {}'.format(recv, log_folder))

    @pytest.fixture(scope='function')
    def log(self, log_folder):
        '''
        setup for each test, runtime log with case name
        '''
        fio_log = log_folder + '/linkspeed'
        yield fio_log

    @pytest.fixture(scope='class')
    def result_summary(self, log_folder):
        '''
        Create a summary log for fio test cases
        '''
        summary_file = log_folder + '/Link_Speed_Dynamic_Change.log'
        yield summary_file

    def test_linkspeed(self, get_parameter, log, result_summary):
        '''
        Main body of the fio test
        Para:
        log: the setup function to get the fio log
        fio_config: fio config got from config file
        '''
        global flag
        flag = 2
        loop, interval = get_parameter
        pci = find_marvell_pci().strip()
        logging.info("marvell pcie id is {}".format(pci))
        t1 = threading.Thread(target=monitor_aer, args=(pci, log))
        t1.start()
        time.sleep(20)
        flag = link_speed_change(interval, loop, pci, log)
        logging.info(flag)
        with open(result_summary, 'a+') as f:
            if flag == -1:
                logging.error(" link speed change have error")
                f.write('%-25s:%-35s\n' % ("link_speed"+interval, 'Fail'))
                pytest.fail('Failed due to link speed change met error.')
            else:
                result = 'Pass'
                f.write('%-25s:%-35s\n' % ("link_speed"+interval, result))
        t1.join()
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
import logging
import os
import subprocess

class Test_get_testbed_info_cmd:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global test_result, test_flag
        test_result = 'testbed_info_result.log'
        fd = open(test_result, 'w')
        fd.write('[Testbed_info]\n')
        fd.close()
        test_flag = 0

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        if test_flag == -1:  # test for CI
            logging.error("CI test and former test failed, abort test")
            pytest.exit("Former test failed, abort test")

    def linux_cmd(self, cmd):
        logging.info('Execute CMD: {}'.format(cmd))
        p1 = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        result = p1.stdout.read().decode()
        logging.info('Result: {}'.format(result))
        return result
     
    @pytest.mark.timeout(timeout=180,method="signal")
    def test_get_testbed_info_cmd(self, hostname):
        global test_result, test_flag
        result = "Fail"        

        try:
            #Host name
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('host_name', hostname))
                
            #Host IP
            cmd = "sudo hostname -I"
            host_ip = self.linux_cmd(cmd)
            host_ip = host_ip.strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('host_ip', host_ip))
            
            #Ubuntu Version
            cmd = "lsb_release -d"
            ubuntu_version = self.linux_cmd(cmd)
            ubuntu_version = ubuntu_version.split(':')
            ubuntu_version = ubuntu_version[-1].strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('ubuntu_version', ubuntu_version))
            
            #Kernel Version
            cmd = "sudo uname -a"
            kernel_version = self.linux_cmd(cmd).strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('kernel_version', kernel_version))
                
            #Mother board
            cmd = "sudo dmidecode -s baseboard-manufacturer"
            mother_board = self.linux_cmd(cmd).strip()
            cmd = "sudo dmidecode -s baseboard-product-name"
            mother_board = mother_board + ' ' + self.linux_cmd(cmd).strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('mother_board', mother_board))
            
            #BIOS
            cmd = "sudo dmidecode -s bios-vendor"
            bios_info = self.linux_cmd(cmd).strip()
            cmd = "sudo dmidecode -s bios-version"
            bios_info = bios_info + ' ' + self.linux_cmd(cmd).strip()
            cmd = "sudo dmidecode -s bios-release-date"
            bios_info = bios_info + ' ' + self.linux_cmd(cmd).strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('bios_info', bios_info))          
            
            #CPU
            cmd = 'lscpu | grep \'Model name:\''
            cpu = self.linux_cmd(cmd)
            cpu = cpu.split(':')
            cpu = cpu[-1].strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('cpu', cpu))
                
            #Cores
            cmd = 'lscpu | grep \'^CPU(s):\''
            cores = self.linux_cmd(cmd)
            cores = cores.split(':')
            cores = cores[-1].strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('cores', cores))           
            
            #SFVS Version
            cmd = 'pip list | grep \'sfvs\''
            sfvs_version = self.linux_cmd(cmd)
            sfvs_version = sfvs_version.split(' ')
            sfvs_version = sfvs_version[-1].strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('sfvs_version', sfvs_version))     
                           
            #FIO Version
            cmd = 'fio --version'
            fio_version = self.linux_cmd(cmd).strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('fio_version', fio_version))             
            
            #PCIe Link Speed
            cmd = 'sudo lspci | grep \'Marvell\''
            tmp = self.linux_cmd(cmd)
            tmp = tmp.split(' ')
            tmp = tmp[0].strip()
            cmd = 'sudo lspci -s '+ tmp + ' -vvv |grep \'LnkSta:\''
            pcie_link_speed = self.linux_cmd(cmd)
            pcie_link_speed = pcie_link_speed.split(':')
            pcie_link_speed = pcie_link_speed[-1].strip()
            with open(test_result, "a+") as f:
                f.write("{}: {}\n".format('pcie_link_speed', pcie_link_speed))             
            
            result = "Pass"
            
        except Exception as e:
            logging.error("Gettestbed info test failed:{}".format(e))
            logging.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        finally:
            if result == "Fail":
                test_flag = -1
                pytest.fail("test_get_testbed_info_cmd failed")
                
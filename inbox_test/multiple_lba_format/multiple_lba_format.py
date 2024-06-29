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
import sys
sys.path.append("../")
from common import fvt_adm_cmd_common
from common import xml_analysis
import time 

class Test_multiple_lba_format:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global test_result, test_flag, log_folder
    
        folder_name = "multiple_lba_format_logs"

        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        
        test_result = 'multiple_lba_format_result.log'
        fd = open(test_result, 'w')
        fd.write('[multiple_lba_format]\n')
        fd.close()
        test_flag = 0

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        if test_flag == -1:  # test for CI
            logging.error("CI test and former test failed, abort test")
            pytest.fail("Former test failed, abort test")
        yield
        if test_flag == -1:  # test for CI
            logging.error("Test_multiple_lba_format failed")
            pytest.fail("Test_multiple_lba_format failed")
        
    def vail_record_result(self, fileName, info, type):
        fd = open(fileName, type)
        if info != None:
            fd.write(info)
        fd.close()
    
    def fio_test(self, hostname, fio_log_folder, fiocase, lba_size, perf_flag, report):

        cmd = "cd ../fio/ ;sudo pytest test_fio.py --disable-warnings --case_suite=" + fiocase + " --lba_size=" + lba_size + " --perf=" + str(perf_flag) + " -s --junitxml=" + report
        os.system(cmd)

        cmd = "cd ../fio/ ;sudo mv " + report + ' ' + fio_log_folder
        os.system(cmd)

        cmd = "cd ../fio/ ;sudo mv " + hostname + "_FIO_logs " + fio_log_folder
        os.system(cmd)
     
    @pytest.mark.timeout(timeout=180,method="signal")
    def test_multiple_lba_format(self, hostname, controller, namespace, test_flow, test_type):
        global test_result, test_flag, log_folder
        result = "Fail"     
        erase_drive = 0
        if test_flow == 'E2e':
            fiocase = 'simple-fio'
            erase_drive = 1
            if test_type == 'postcommit':
                LBAF_item_list = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '14']
            elif test_type == 'precommit':
                LBAF_item_list = ['0', '5', '6', '12']

        elif test_flow == 'Ramdrive':
            fiocase = 'simple-fio-ramdrive'
            erase_drive = 0
            if test_type == 'postcommit':
                LBAF_item_list = ['0', '1', '5', '7', '12', '14']
            elif test_type == 'precommit':
                LBAF_item_list = ['0', '5', '12']
    
        size_512b = ['0', '9', '10', '11', '12', '13', '14', '15', '16']
        size_4k = ['1', '2', '3', '4', '5', '6', '7', '8']
        
        try:
            adm_common = fvt_adm_cmd_common.fvt_adm(controller, namespace)
            for lbaf in LBAF_item_list:
                if lbaf in size_512b:
                    lba_size = '512b'
                elif lbaf in size_4k:
                    lba_size = '4k'   
                    
                t_beginning = time.time()    

                adm_common = fvt_adm_cmd_common.fvt_adm(controller, namespace)
                ret = adm_common.format(int(lbaf), erase_drive, 'vail')
                if ret != 0:
                    logging.error("NVMe format failed") 
                    pytest.fail("NVMe format failed") 
                else:
                    logging.info("Format device to LBA {}".format(lbaf))
                        
                fio_log_folder = log_folder+'/LBAF'+lbaf
                if not os.path.exists(fio_log_folder):
                    os.mkdir(fio_log_folder)
                    
                perf_flag = "False"
                report = 'fio_lbaf_'+lbaf + "_result.xml"
                self.fio_test(hostname, fio_log_folder, fiocase, lba_size, perf_flag, report)
                result = xml_analysis.xml_analysis(fio_log_folder + "/" + report)
                t_end = time.time() 
                self.vail_record_result(test_result, "/LBAF"+lbaf+":", 'a+')
                if result == 0:
                    self.vail_record_result(test_result, "PASS:", 'a+')
                else:
                    logging.error("LBAF {}, fio FAIL".format(lbaf)) 
                    self.vail_record_result(test_result, "FAIL:", 'a+')
                    pytest.fail()
                
                spend_time = str(int(t_end-t_beginning))+'\n'
                self.vail_record_result(test_result, spend_time , 'a+')
            logging.info("MLBA all pass, return to default format: LBAF1")
            ret = adm_common.format(int(1), erase_drive, 'vail')
            result = 'Pass'
        except:
            result = "Fail"
            test_flag = -1
            logging.error("test_multiple_lba_format meet except failed") 
        finally:
            if result != 'Pass':
                test_flag = -1
                logging.error("test_multiple_lba_format: FAIL") 
                pytest.fail("test_multiple_lba_format: FAIL")
            
                
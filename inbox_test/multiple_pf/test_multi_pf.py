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
import time, os, shutil
import multi_pf_util
import random
import subprocess
import math

class Test_Multi_PF:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global multi_pf_result, test_flag
        folder_name = hostname + "_multi_pf_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        test_flag = 0
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        multi_pf_result = log_folder + '/multi_pf_result.log'
        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        '''
        3 scenario:
        #1: check multi-pf failed, all should fail
        #2: for CI, one test fail, stop others
        #3: for integration, continue other tests even former failed
        '''
        global test_flag
        if test_flag == 1:
            pytest.exit("Multi-PF check failed, abort test") 
        elif test_flag == -1 and request.node.get_closest_marker("ci_precommit") != None:  # test for CI
            logging.error("CI test and former test failed, abort test")
            pytest.exit("Former test failed, abort test")
                 

    @pytest.mark.timeout(timeout=300,method="signal")
    def test_multi_pf_basic(self, pf_amount):
        '''
        Check if PF activated as expected, i.e. expected amount of NS detected  
        '''
        global multi_pf_result, test_flag
        logging.info("++++Test start: Multi-PF basic++++")
        result = "Fail"
        try:
            ns_list = multi_pf_util.check_get_pf(pf_amount)
            if ns_list == -1:
                logging.error("Multi-PF check failed, abort test")
            else:
                nsze_refer = multi_pf_util.get_specified_id_value(ns_list[0], "nsze")
                for ns in ns_list:
                    nsze_temp = multi_pf_util.get_specified_id_value(ns, "nsze")
                    if nsze_temp != nsze_refer:
                        logging.error("All NS size should be the same, but found difference on {}".format(ns))
                        break
                else:
                    result = "Pass"

        except Exception as e:
            logging.error("Exception met during Multi-PF basic test:{}".format(e))
        
        finally:
            logging.info("++++Test completed: Multi-PF basic++++")
            with open(multi_pf_result, "a+") as f:
                f.write("Multi_pf basic {}pf: {}\n".format(pf_amount, result))

            if result == "Fail":
                test_flag = 1  # this value only for this test
                pytest.fail("Multi-PF basic test failed") # following tests depend on this

    @pytest.mark.timeout(timeout=1800,method="signal")
    def test_multi_pf_io_basic(self, pf_amount, build):
        '''
        Write on one PF and read on another
        @Overall design(due to limitation that no overwrite allowed:
        on this test, step 1. write 0-10% on one PF, step 2. on another PF, randread 0-10% and write 10%-20% at the same time
        '''
        global multi_pf_result, test_flag
        time.sleep(5)
        logging.info("++++Test start: Multi-PF io basic++++")
        result = "Fail"
        fio_log_folder = "multi_pf_io_basic_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)

        ns_list = multi_pf_util.get_all_ns()

        if build == "Ramdrive":
            range_start = 0
            range = "100%"
        else:
            basic_range = multi_pf_util.parse_config("basic_range")
            range = str(int(basic_range[:-1]) // 2) + basic_range[-1]
            range_start = range
        
        try:
            ns = ns_list[random.randint(0, pf_amount - 1)]
            logging.info("Do write on NS: {}".format(ns))
            wr_log, rw_log, rd_log = multi_pf_util.fio_on_ns(ns, offset = 0, size = range, log_folder = fio_log_folder, io_type = "write")
            if multi_pf_util.check_fio_result(wr_log) != "Pass":
                logging.error("Write on NS failed, log file: {}".format(wr_log))
                pytest.fail("Write on NS failed, log file: {}".format(wr_log))

            logging.info("Do read/write on another PF")
            ns_list.remove(ns)
            ns_read = ns_list[random.randint(0, pf_amount - 2)]
            wr_log, rw_log, rd_log = multi_pf_util.fio_on_ns(ns_read, offset = range_start, size = range, log_folder = fio_log_folder, io_type = "mix", readsize = range)
            # check FIO test result
            if multi_pf_util.check_fio_result(rw_log) != "Pass":
                logging.error("Write and Read verify on other PFs failed, log file: {}".format(rw_log))
                pytest.fail("Write and Read Read and verify on other PFs failed, log file: {}".format(rw_log))
            
            result = "Pass"
        except Exception as e:
            logging.error("Exception met during Multi-PF io basic test:{}".format(e))

        finally: 
            logging.info("++++Test completed: Multi-PF io basic test++++")
            with open(multi_pf_result, "a+") as f:
                f.write("Multi Pf io basic: {}\n".format(result))
            
            if result == "Fail":
                test_flag = -1
                pytest.fail("Multi-PF io basic test failed")

    @pytest.mark.timeout(timeout=3600,method="signal")
    def test_multi_pf_stress(self, pf_amount, build):
        '''
        @Continued: Overall design(due to limitation that no overwrite allowed:
        on this test, step 1 - on all PFs at the same time: randread 0-10% + write 20%-100% at the same time for 16 PFs(different range for each due to limitation)
        step 2 - parallel read on all PFs for full disk
        '''
        global multi_pf_result, test_flag
        time.sleep(5)
        logging.info("++++Test start: Multi-PF stress++++")
        result = "Fail"
        fio_log_folder = "multi_pf_io_stress_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)

        ns_list = multi_pf_util.get_all_ns()

        if build == "Ramdrive":
            basic_range = "0%"
            stress_range = "100%"
            verify_range = "100%"
        else:
            stress_range = multi_pf_util.parse_config("stress_range")
            basic_range = multi_pf_util.parse_config("basic_range")
            verify_range = str(int(stress_range[:-1]) + int(basic_range[:-1])) + stress_range[-1]

        try:
            
            if build == "Ramdrive":
                logging.info("Do write/read on all NS at the same time")
                multi_pf_util.run_io_on_namespaces(ns_list, offset_overall = basic_range, size_overall = stress_range, log_folder = fio_log_folder, io_type = "mix", split_flag = False, readsize = stress_range)
            else: ####Due to zero read limitation, currently for E2e, no parallel write allowed
                logging.info("For E2e, temperarily do write on one NS and read for the rest of the drive")
                multi_pf_util.fio_on_ns(ns_list[random.randint(0, pf_amount - 2)], offset = basic_range, size = stress_range, log_folder = fio_log_folder, io_type = "write")
            # check all FIO test result
            fio_logs = []
            for root, dirs, files in os.walk(fio_log_folder):
                for file in files:
                    if os.path.splitext(file)[1] == '.log':  
                        fio_logs.append(os.path.join(root, file))  
            for log in fio_logs:
                if multi_pf_util.check_fio_result(log) != "Pass":
                    test_flag = -1
                    logging.error("Write/read on all NS failed, log file: {}".format(log))
                    pytest.fail("Write/read on all NS failed, log file: {}".format(log))

            logging.info("Do read and verify on all PFs")
            multi_pf_util.run_io_on_namespaces(ns_list, size_overall = verify_range, log_folder = fio_log_folder, io_type = "read", split_flag = False)
            # check all FIO test result
            fio_logs = []
            for root, dirs, files in os.walk(fio_log_folder):
                for file in files:
                    if os.path.splitext(file)[1] == '.log' and "rd" in file:  
                        fio_logs.append(os.path.join(root, file))  
            for log in fio_logs:
                if multi_pf_util.check_fio_result(log) != "Pass":
                    test_flag = -1
                    logging.error("Read and verify on other PFs failed, log file: {}".format(log))
                    pytest.fail("Read and verify on other PFs failed, log file: {}".format(log))
        
            result = "Pass"
        except Exception as e:
            logging.error("Exception met during Multi-PF io stress test:{}".format(e))

        finally: 
            logging.info("++++Test completed: Multi-PF io stress test++++")
            with open(multi_pf_result, "a+") as f:
                f.write("Multi Pf io stress: {}\n".format(result))
            
            if result == "Fail":
                test_flag = -1
                pytest.fail("Multi-PF io stress test failed")

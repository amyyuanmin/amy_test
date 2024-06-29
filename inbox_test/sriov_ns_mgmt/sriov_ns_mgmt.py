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

from curses.ascii import ctrl
import pytest
import time, os, shutil
import sriov_ns_mgmt_util as sriov_ns_mgmt
import random
#from log_util.log_config import MyLog
from log_config import MyLog
import sys
sys.path.append("../")
from common.uart_util import UART_Util
import time
#SDK limitation: value of -s should be the same as -c during create-ns action
#delete-ns should be in descending order
#The latest design of SDK, all controller under the same subsystem. The indicator of NS is visually named under the same nvme number: 
# i.e. nvmeXnY, the X is fixed but might not be 0. Only Y is increasing as more and more NS created.
class Test_Sriov_NS_Mgmt:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname, rpi_ip, rpi_path):
        global sriov_result, ns_mgmt_result, test_flag, logger, uart_util
        folder_name = hostname + "_SRIOV_NS_MGMT_logs"

        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)
        
        test_flag = 0
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        sriov_result = log_folder + '/sriov_result.log'
        ns_mgmt_result = log_folder + '/ns_mgmt_result.log'
        uart_util = UART_Util(rpi_ip, rpi_path)
        
        logger = MyLog(log_folder + "/runtime_console.log")
        
        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        '''
        3 scenario:
        #1: enable SRIOV failed, all should fail
        #2: for CI, one test fail, stop others
        #3: for integration, continue other tests even former failed
        '''
        global test_flag
        if test_flag == 1:
            pytest.exit("Enable SRIOV failed, abort test")  # only for SRIOV which should be the precondition for all tests
        elif test_flag == -1 and request.node.get_closest_marker("ci_precommit") != None:  # test for CI
            logger.error("CI test and former test failed, abort test")
            pytest.exit("Former test failed, abort test")
        yield 
        
        if request.node.name != "test_sriov_basic":
            logger.info("UART Format to clear drive at teardown")
            uart_util.uart_format()

    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=300,method="signal")
    def test_sriov_basic(self, vf_amount):
        '''
        enable vf with various amount, 33 is value beyond the max.  
        add check of tnvmcap to compare with value of total size.
        '''
        global sriov_result, test_flag
        logger.info("++++Test start: Sriov basic++++")
        result = "Fail"
        try:
            enable_ret = sriov_ns_mgmt.enable_sriov(vf_amount)
            if enable_ret != 0:
                logger.error("Enable SRIOV failed, abort test")
            else:
                result = "Pass"
                time.sleep(60) # delay some time to let fw ready

        except Exception as e:
            logger.error("Exception met during sriov basic test:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        
        finally:
            logger.info("++++Test completed: Sriov basic, result:{}++++".format(result))
            with open(sriov_result, "a+") as f:
                f.write("Sriov basic {}vf: {}\n".format(vf_amount, result))

            if result == "Fail":
                test_flag = 1  # this value only for this test
                pytest.fail("SRIOV basic test failed") # following tests depend on this

    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=300,method="signal")
    def test_sriov_vf_basic(self, vf_amount):
        '''
        Should follow test above with SRIOV enabled
        Pick any VF among 32 VFs
        '''
        global sriov_result, test_flag
        time.sleep(15)  # some time to let system ready
        logger.info("++++Test start: Sriov VF basic IO++++")
        fio_log_folder = "sriov_vf_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        result = "Fail"
        tests = sriov_ns_mgmt.ns_mgmt_basic()
        try:
            for test in tests:
                ns_list_before = sriov_ns_mgmt.check_get_real_ns()
                ctrl_id = random.randint(1, vf_amount)
                ctrl = "/dev/nvme{}".format(ctrl_id)
                size = hex(test['size'])  # no idea why the value here converted to int, and the NS size is wired, 0x20000 -> 536M, but 131072 -> 33M
                capacity = hex(test['capacity'])
                flba = test['flba']
                dps = test['dps']
                shared = test['shared']
                ns_id = '1' # ns_id is 1 since only 1 created
                logger.info("Create NS for test")
                if sriov_ns_mgmt.ns_create(ctrl, size, capacity, flba, dps, shared) == 0:
                    if sriov_ns_mgmt.ns_attach(ns_id, [ctrl_id]) == 0: 
                        sriov_ns_mgmt.rescan_ctrl([ctrl_id])
                        time.sleep(2)
                        ns_list = sriov_ns_mgmt.check_get_real_ns()
                        ns = [i for i in ns_list if i not in ns_list_before]
                        if ns != []:
                        # run IO on NS
                            ns = ns[0]
                            wr_log, rd_log, rw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type="write_mix")
                            if sriov_ns_mgmt.check_fio_result(wr_log) == "Pass" and sriov_ns_mgmt.check_fio_result(rw_log) == "Pass":
                                logger.info("The last step: Clear env...")
                                if sriov_ns_mgmt.ns_detach(ns_id, [ctrl_id]) == 0:
                                    if sriov_ns_mgmt.ns_delete(ctrl, ns_id) == 0:
                                        result = "Pass"

        except Exception as e:
            logger.error("Exception met during VF basic IO test:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        
        finally:
            logger.info("++++Test completed: Sriov basic IO, result: {}++++".format(result))
            with open(sriov_result, "a+") as f:
                f.write("Sriov basic IO: {}\n".format(result))
                
            if result == "Fail":
                test_flag = -1
                # detach and delete ns as teardown, do not expect to succeed
                logger.info("Clearing env after test execution, possible failure here doesnot affect test result")
                sriov_ns_mgmt.ns_detach(ns_id, [ctrl_id], expect_fail = True)
                sriov_ns_mgmt.ns_delete(ctrl, ns_id, expect_fail = True)
                sriov_ns_mgmt.rescan_ctrl([ctrl_id])
                pytest.fail("SRIOV basic IO test failed")
    
    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=300,method="signal")
    @pytest.mark.parametrize('function', ['PF', 'VF'])
    def test_ns_mgmt_basic(self, function, vf_amount):
        '''
        basic ns mgmt function on PF/VF, create/attach/detach/delete NS 
        identify values check as well
        identify namespace NVMCAP should be supported in NS MGMT supported
        identify controller TNVMCAP/UNVMCAP should be supported(not 0) in NS MGMT supported
        identify controller, the bit 3 of OACS should be 1. value of nn should be 300
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: NS mgmt {} basic++++".format(function))
        result = "Fail"
        fio_log_folder = "ns_mgmt_basic_{}_fio_logs".format(function.lower())
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        tests = sriov_ns_mgmt.ns_mgmt_basic()
        try:
            for test in tests:
                ns_list_before = sriov_ns_mgmt.check_get_real_ns()
                if function == "PF":
                    ctrl_id = 0 # PF is nvme0
                elif function == "VF":
                    ctrl_id = random.randint(1, vf_amount)  # randomly pick a VF controller
                ctrl = "/dev/nvme{}".format(ctrl_id)
                size = hex(test['size'])  # no idea why the value here converted to int 
                capacity = hex(test['capacity'])
                flba = test['flba']
                dps = test['dps']
                shared = test['shared']
                ns_id = '1' # ns_id is 1 since only 1 created
                logger.info("Create NS for test")
                if sriov_ns_mgmt.ns_create(ctrl, size, capacity, flba, dps, shared) == 0:
                    if sriov_ns_mgmt.ns_attach(ns_id, [ctrl_id]) == 0: 
                        sriov_ns_mgmt.rescan_ctrl([ctrl_id])
                        ns_list = sriov_ns_mgmt.check_get_real_ns()
                        ns = [i for i in ns_list if i not in ns_list_before]
                        if ns != []:
                            ns = ns[0]
                        # check identify
                            capacity_check = str(int(capacity, 16) * 4096)  # capacity is in LBA, need to transfer to byte
                            if sriov_ns_mgmt.check_identify_values(ns, "NVMCAP", capacity_check) == "Passed" and \
                                sriov_ns_mgmt.check_nvmcap(ctrl) == "Passed" and \
                                    sriov_ns_mgmt.check_identify_values(ctrl, "NN", "300") == "Passed" and \
                                        sriov_ns_mgmt.check_identify_values(ctrl, "OACS") == "Passed":
                                # run IO on NS
                                wr_log, rd_log, rw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type="write_mix")
                                if sriov_ns_mgmt.check_fio_result(wr_log) == "Pass" and sriov_ns_mgmt.check_fio_result(rw_log) == "Pass":
                                    logger.info("The last step: Clear env...")
                                    if sriov_ns_mgmt.ns_detach(ns_id, [ctrl_id]) == 0:
                                        if sriov_ns_mgmt.ns_delete(ctrl, ns_id) == 0:
                                            result = "Pass"
        except Exception as e:
            logger.error("Exception met during {} basic test:{}".format(function, e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        
        finally:
            logger.info("++++Test completed: NS mgmt {} basic, result:{}++++".format(function, result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("NS mgmt {} basic: {}\n".format(function, result))

            if result == "Fail":
                test_flag = -1
                # detach and delete ns as teardown, do not expect to succeed
                logger.info("Clearing env after test execution, possible failure here doesnot affect test result")
                sriov_ns_mgmt.ns_detach(ns_id, [ctrl_id], expect_fail = True)
                sriov_ns_mgmt.ns_delete(ctrl, ns_id, expect_fail = True)
                sriov_ns_mgmt.rescan_ctrl([ctrl_id])
                pytest.fail("NS mgmt {} basic test failed".format(function))

    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=2400,method="signal")
    def test_ns_create_multi_lbaf(self):
        '''
        1. create multiple NS with different LBAF
        2. Check identify values, flbas, lbads, lbaf
        3. Do basic IO on all created NS
        update for #3: Limitation of Multi-NS, only allow write on one NS at one time.
        Step for #3: 1. write first 50% of each NS one by one.
        2. do mix rw(read first 50%, write last 50%) of each NS one by one, at the same time do read first 50% at all NS
        3. do full read of all NS 
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: NS create with multiple LBAF++++")
        result = "Fail"
        fio_log_folder = "ns_create_multi_lbaf_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        supported_flbaf = sriov_ns_mgmt.parse_config("supported_lbaf")
        try:
            tests = sriov_ns_mgmt.ns_mgmt_cases(16, shared_flag = 0, flbaf_list = supported_flbaf) 
            if tests == -1:
                test_flag = -1
                pytest.fail("Cannot achive max capacity of device which shall be supported if NS mgmt supported, please check")
            ns_list = []
            ctrl_id_list = []
            ctrl_id = 0  
            ns_id = 1
            logger.info("Create NS for test with differnt LBAF")
            for test in tests:
                ns_list_before = sriov_ns_mgmt.check_get_real_ns()
                ctrl_id_list.append(ctrl_id)
                flba = test['flba']
                logger.debug("Create NS - index: {} (start from 1), LBAF: {}".format(ctrl_id + 1, flba))
                ctrl = test['controller']
                size = test['size']  # no idea why the value here converted to int 
                capacity = test['capacity']
                dps = test['dps']
                shared = test['shared']
                if flba in ['0', '9', '10', '11', '12', '13', '14', '15']:
                    lba_size = 512
                else:
                    lba_size = 4096
                if sriov_ns_mgmt.ns_create(ctrl, size, capacity, flba, dps, shared) == 0:
                    if sriov_ns_mgmt.ns_attach(ns_id, [ctrl_id]) == 0: 
                        sriov_ns_mgmt.rescan_ctrl([ctrl_id])
                        ns_list = sriov_ns_mgmt.check_get_real_ns()
                        ns = [i for i in ns_list if i not in ns_list_before]
                        if ns != []:
                            ns = ns[0]
                            # check identify
                            capacity_check = str(int(capacity, 16) * lba_size)  # capacity is in LBA, need to transfer to byte
                            if sriov_ns_mgmt.check_identify_values(ns, "NVMCAP", capacity_check) == "Passed" and \
                                sriov_ns_mgmt.check_flbaf(ns, flba) == "Passed":
                                ns_list.append(ns)
                            else:
                                logger.error("Identify check failed")
                                pytest.fail("Identify check failed")
                        else:
                            logger.error("NS attach succeed, but no NS detected")
                            pytest.fail("NS attach succeed, but no NS detected")
                    else:
                        logger.error("NS attach failed")
                        pytest.fail("NS attach failed")
                else:
                    logger.error("NS create failed")
                    pytest.fail("NS create failed")
                ctrl_id += 1
                ns_id += 1
            ns_list = sriov_ns_mgmt.check_get_real_ns()
            logger.info("Do basic IO on all namespaces")
            for ns in ns_list:
                seqwr_log, seqrd_cmd, seqrw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type = "write_mix")
                if sriov_ns_mgmt.check_fio_result(seqrw_log) != "Pass" or sriov_ns_mgmt.check_fio_result(seqwr_log) != "Pass":
                    test_flag = -1
                    logger.error("IO on NS failed, log file: {}".format(seqrw_log))
                    pytest.fail("IO on NS failed, log file: {}".format(seqrw_log))
            
            sriov_ns_mgmt.run_io_on_namespaces(ns_list, fio_log_folder, "read", size = "100%")

            # check all FIO test result
            sriov_ns_mgmt.check_fio_logs(fio_log_folder)
            
            logger.info("The last step: Clear env...")
            
            for i in range(0, len(ns_list)):
                if sriov_ns_mgmt.ns_detach((i + 1), [i]) != 0:
                    logger.error("NS Detach failed: {}".format(ns_list[i]))
                    pytest.fail("NS Detach failed")

            for i in range(len(ns_list), 0, -1):
                if sriov_ns_mgmt.ns_delete("/dev/nvme0", i, expect_fail = True) != 0: # delete all in decending order
                    logger.error("NS Delete failed: {}".format(ns_list[i]))
                    pytest.fail("NS Delete failed")

            result = "Pass"  # if reach here, test should passed, since if fail met, pytest.fail executed
        except Exception as e:
            logger.error("Exception met during NS create with multiple LBAF: {}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        
        finally:
            logger.info("++++Test completed: NS create with multiple LBAF, result: {}++++".format(result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("NS create with multiple LBAF: {}\n".format(result))

            if result == "Fail":
                test_flag = -1
                # detach and delete ns as teardown, do not expect to succeed
                logger.info("Clearing env after test execution, possible failure here doesnot affect test result")
                for i in range(0, len(ns_list)):
                    sriov_ns_mgmt.ns_detach((i + 1), [i], expect_fail = True)

                for i in range(len(ns_list), 0, -1):
                    sriov_ns_mgmt.ns_delete("/dev/nvme0", i, expect_fail = True) # delete all in decending order
                sriov_ns_mgmt.rescan_ctrl(ctrl_id_list)
                pytest.fail("NS create with multiple LBAF test failed")

    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=2400,method="signal")
    def test_multiple_ns_format_mlbaf(self):
        '''
        pick some NS to format to different LBAF, and do basic IO
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: Format to different LBAF on multiple NS++++")
        result = 'Fail'
        fio_log_folder = "ns_format_mlbaf_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        
        supported_flbaf = sriov_ns_mgmt.parse_config("supported_lbaf")

        try:
            tests = sriov_ns_mgmt.ns_mgmt_cases(16)  # at most 16 LBAF for NVMe
            if tests == -1:
                test_flag = -1
                pytest.fail("Cannot achive max capacity of device which shall be supported if NS mgmt supported, please check")
            ns_list = []
            ns_list_before = []
            ctrl_id_list = []
            ctrl_id = 0 
            ns_id = 1       
            logger.info("Create NS for test")
            for test in tests[0:len(supported_flbaf)]:
                ns_list_before = sriov_ns_mgmt.check_get_real_ns()
                ctrl_id_list.append(ctrl_id)
                flba = test['flba']
                logger.debug("Create NS - index: {} (start from 1), LBAF: {}".format(ctrl_id + 1, flba))
                ctrl = test['controller']
                size = test['size']
                capacity = test['capacity']
                dps = test['dps']
                shared = test['shared']
                if flba in ['0', '9', '10', '11', '12', '13', '14', '15']:
                    lba_size = 512
                else:
                    lba_size = 4096
                if sriov_ns_mgmt.ns_create(ctrl, size, capacity, flba, dps, shared) == 0:
                    if sriov_ns_mgmt.ns_attach(ns_id, [ctrl_id]) == 0: 
                        sriov_ns_mgmt.rescan_ctrl([ctrl_id])
                        ns_list = sriov_ns_mgmt.check_get_real_ns()
                        ns = [i for i in ns_list if i not in ns_list_before]
                        if ns != []:
                            ns = ns[0]
                            capacity_check = str(int(capacity, 16) * lba_size)  # capacity is in LBA, need to transfer to byte
                            flba = supported_flbaf[ctrl_id]
                            if sriov_ns_mgmt.format_ns(ns, ns_id, flba, '0') == 0:
                                # check identify
                                if sriov_ns_mgmt.check_identify_values(ns, "NVMCAP", capacity_check) == "Passed" and \
                                    sriov_ns_mgmt.check_flbaf(ns, flba) == "Passed":
                                    ns_list.append(ns)
                                else:
                                    logger.error("Identify check failed")
                                    pytest.fail("Identify check failed")
                            else:
                                logger.error("Format to {} failed".format(flba))
                                pytest.fail("Format to {} failed".format(flba))
                        else:
                            logger.error("NS attach succeed, but no NS detected")
                            pytest.fail("NS attach succeed, but no NS detected")
                    else:
                        logger.error("NS attach failed")
                        pytest.fail("NS attach failed")
                else:
                    logger.error("NS create failed")
                    pytest.fail("NS create failed")
                ctrl_id += 1
                ns_id += 1
            ns_list = sriov_ns_mgmt.check_get_real_ns()
            logger.info("Do basic IO on all available NS")
            
            for ns in ns_list:
                seqwr_log, seqrd_cmd, seqrw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type = "write_mix")
                if sriov_ns_mgmt.check_fio_result(seqrw_log) != "Pass" or sriov_ns_mgmt.check_fio_result(seqwr_log) != "Pass":
                    test_flag = -1
                    logger.error("IO on NS failed, log file: {}".format(seqrw_log))
                    pytest.fail("IO on NS failed, log file: {}".format(seqrw_log))
            
            sriov_ns_mgmt.run_io_on_namespaces(ns_list, fio_log_folder, "read", size = "100%")

            # check all FIO test result
            sriov_ns_mgmt.check_fio_logs(fio_log_folder)
            
            logger.info("The last step: Clear env...")
                
            for i in range(0, len(ns_list)):
                if sriov_ns_mgmt.ns_detach((i + 1), [i]) != 0:
                    logger.error("NS Detach failed: {}".format(ns_list[i]))
                    pytest.fail("NS Detach failed")

            for i in range(len(ns_list), 0, -1):
                if sriov_ns_mgmt.ns_delete("/dev/nvme0", i) != 0: # delete all in decending order
                    logger.error("NS Delete failed: {}".format(ns_list[i-1]))
                    pytest.fail("NS Delete failed")
            sriov_ns_mgmt.rescan_ctrl(ctrl_id_list)
                
            result = "Pass"  # if reach here, test should passed, since if fail met, pytest.fail executed
        except Exception as e:
            logger.error("Exception met during test Format to different LBAF on multiple NS:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))

        finally: # finally will be executed no matter what happens on try/except
            logger.info("++++Test completed: Format to different LBAF on multiple NS, result:{}++++".format(result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("Format to different LBAF on multiple NS: {}\n".format(result))

            if result == "Fail":
                # clear env, detach and delete all create NS, as teardown
                logger.info("Clearing env after test execution, possible failure here doesnot affect test result")
                for i in range(0, len(ns_list)):
                    sriov_ns_mgmt.ns_detach((i + 1), [i], expect_fail = True)

                for i in range(len(ns_list), 0, -1):
                    sriov_ns_mgmt.ns_delete("/dev/nvme0", i, expect_fail = True) # delete all in decending order
                sriov_ns_mgmt.rescan_ctrl(ctrl_id_list)
                test_flag = -1
                pytest.fail("Format to different LBAF on multiple NS failed")

    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=3600,method="signal")
    def test_io_multiple_ns(self, vf_amount):
        '''
        1PF + 32VF, create one namespace on each, attach for each, do basic IO
        update for basic IO: Limitation of Multi-NS, only allow write on one NS at one time.
        Step for basic IO: 1. write first 50% of each NS one by one.
        2. do mix rw(read first 50%, write last 50%) of each NS one by one, at the same time do read first 50% at all NS
        3. do full read of all NS 
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: NS mgmt IO on multiple NS++++")
        result = 'Fail'
        fio_log_folder = "io_on_multi_ns_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        ns_amount = vf_amount + 1
        ctrl_amount = vf_amount + 1
        ctrl_list = []
        for i in range(0, ctrl_amount):
            ctrl_list.append(i)
        try:
            tests = sriov_ns_mgmt.ns_mgmt_cases(ns_amount)  # 33 NS, one for each controller
            if tests == -1:
                test_flag = -1
                pytest.fail("Cannot achive max capacity of device which shall be supported if NS mgmt supported, please check")
            attached_ns_list = []
            index = 1     
            logger.info("Create NS for test")  
            for test in tests:
                logger.debug("Create NS - index: {} (start from 1)".format(index))
                controller = test['controller']
                size = test['size']
                capacity = test['capacity']
                flba = test['flba']
                dps = test['dps']
                shared = test['shared']
                if sriov_ns_mgmt.ns_create(controller, size, capacity, flba, dps, shared) != 0:
                    test_flag = -1
                    pytest.fail("Create NS failed")
                index += 1
            ns_amount_list = sriov_ns_mgmt.spread_nonshared_ns_to_ctrl(ns_amount, ctrl_amount, 'random')
            ns_amount_starter = 1
            # attach spcified number(listed in ns_amount_list) of NS to controllers
            for i in range(0, len(ns_amount_list)):
                for k in range(ns_amount_starter, ns_amount_starter + ns_amount_list[i]):
                    if sriov_ns_mgmt.ns_attach(k, [i]) != 0:
                        test_flag = -1
                        pytest.fail("Attach NS failed")
                    attached_ns_list.append("/dev/nvme{}n{}".format(i, (k - ns_amount_starter + 1)))
                ns_amount_starter = ns_amount_starter + ns_amount_list[i]
            logger.info("Attached NS list: {}".format(attached_ns_list))

            sriov_ns_mgmt.rescan_ctrl(ctrl_list) # rescan each controller
            real_ns_list = sriov_ns_mgmt.check_get_real_ns()
            if len(attached_ns_list) != len(real_ns_list):
                test_flag = -1
                pytest.fail("Not all expected NS found, please check")

            for ns in real_ns_list:
                seqwr_log, seqrd_cmd, seqrw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type = "write_mix")
                if sriov_ns_mgmt.check_fio_result(seqrw_log) != "Pass" or sriov_ns_mgmt.check_fio_result(seqwr_log) != "Pass":
                    test_flag = -1
                    logger.error("IO on NS failed, log file: {}".format(seqrw_log))
                    pytest.fail("IO on NS failed, log file: {}".format(seqrw_log))
            
            sriov_ns_mgmt.run_io_on_namespaces(real_ns_list, fio_log_folder, "read", size = "100%")
            sriov_ns_mgmt.check_fio_logs(fio_log_folder)

            logger.info("The last step: Clear env...")
            ns_amount_starter = 1
            for i in range(0, len(ns_amount_list)):
                for k in range(ns_amount_starter, ns_amount_starter + ns_amount_list[i]):
                    if sriov_ns_mgmt.ns_detach(k, [i]) != 0:                
                        logger.error("NS Detach failed")
                        pytest.fail("NS Detach failed")
                ns_amount_starter = ns_amount_starter + ns_amount_list[i]

            for i in range(ns_amount, 0, -1):
                if sriov_ns_mgmt.ns_delete("/dev/nvme0", i) != 0:# delete all in decending order
                    logger.error("NS Delete failed")
                    pytest.fail("NS Delete failed")

            result = "Pass"  # if reach here, test should passed, since if fail met, pytest.fail executed
        except Exception as e:
            logger.error("Exception met during test IO on multiple NS:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))

        finally: # finally will be executed no matter what happens on try/except
            logger.info("++++Test completed: NS mgmt IO on multiple NS, result:{}++++".format(result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("NS mgmt IO on multiple NS: {}\n".format(result))

            if result == "Fail":
                test_flag = -1
                # clear env, detach and delete all create NS, as teardown
                logger.info("Clearing env after test execution")
                ns_amount_starter = 1
                for i in range(0, len(ns_amount_list)):
                    for k in range(ns_amount_starter, ns_amount_starter + ns_amount_list[i]):
                        sriov_ns_mgmt.ns_detach(k, [i], expect_fail = True)
                    ns_amount_starter = ns_amount_starter + ns_amount_list[i]
                for i in range(ns_amount, 0, -1):
                    sriov_ns_mgmt.ns_delete("/dev/nvme0", i, expect_fail = True) # delete all in decending order
                sriov_ns_mgmt.rescan_ctrl(ctrl_list)
                pytest.fail("NS mgmt IO on multiple NS test failed")

    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=3600,method="signal")
    def test_ns_capacity(self, vf_amount):
        '''
        1PF + 32VF, 300 NS on an individual controller, spread 300 NS on all controllers.
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: NS Capacity test++++")
        result = 'Fail'
        ns_amount = 300
        ns_amount_list = []
        try:
            tests = sriov_ns_mgmt.ns_mgmt_cases(ns_amount)  # max. amount of NS, i.e. 300 NS
            if tests == -1:
                test_flag = -1
                pytest.fail("Cannot achive max capacity of device which shall be supported if NS mgmt supported, please check")
            index = 1       
            logger.info("Create NS for test")
            for test in tests:
                logger.debug("Create NS - index: {} (start from 1)".format(index))
                controller = test['controller']
                size = test['size'] 
                capacity = test['capacity']
                flba = test['flba']
                dps = test['dps']
                shared = test['shared']
                if sriov_ns_mgmt.ns_create(controller, size, capacity, flba, dps, shared) != 0:
                    test_flag = -1
                    pytest.fail("Create NS failed")
                index += 1
            ######################################
            #for ctrl_amount in [1, vf_amount + 1]: 
            # #Can only run one case at one time, 
            # we need FORMAT cmd, so I test spread 300 NS on all controllers this time
            ###################################
            for ctrl_amount in [1, vf_amount + 1]:
                fio_log_folder = "ns_capacity_fio_logs_{}_controllers".format(ctrl_amount)
                if not os.path.exists(fio_log_folder):
                    os.mkdir(fio_log_folder)
                ctrl_list = []
                attached_ns_list = []
                real_ns_list = []
                for i in range(0, ctrl_amount):
                    ctrl_list.append(i)
                logger.info("300 NS on {} controllers".format(ctrl_amount))
                ns_amount_list = sriov_ns_mgmt.spread_nonshared_ns_to_ctrl(ns_amount, ctrl_amount)
                ns_amount_starter = 1
                # attach spcified number(listed in ns_amount_list) of NS to controllers
                for i in range(0, len(ns_amount_list)):
                    for k in range(ns_amount_starter, ns_amount_starter + ns_amount_list[i]):
                        if sriov_ns_mgmt.ns_attach(k, [i]) != 0:
                            test_flag = -1
                            pytest.fail("Attach NS failed")
                        attached_ns_list.append("/dev/nvme{}n{}".format(i, (k - ns_amount_starter + 1)))
                    ns_amount_starter = ns_amount_starter + ns_amount_list[i]
                logger.debug("Attached NS list: {}".format(attached_ns_list))

                sriov_ns_mgmt.rescan_ctrl(ctrl_list) # rescan each controller
                real_ns_list = sriov_ns_mgmt.check_get_real_ns()  
                if len(attached_ns_list) != len(real_ns_list):
                    test_flag = -1
                    pytest.fail("Not all expected NS found, please check")
                    
                for ns in real_ns_list:
                    seqwr_log, seqrd_cmd, seqrw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type = "write_mix")
                    if sriov_ns_mgmt.check_fio_result(seqrw_log) != "Pass" or sriov_ns_mgmt.check_fio_result(seqwr_log) != "Pass":
                        test_flag = -1
                        logger.error("IO on NS failed, log file: {}".format(seqrw_log))
                        pytest.fail("IO on NS failed, log file: {}".format(seqrw_log))                
                    
                sriov_ns_mgmt.run_io_on_namespaces(real_ns_list, fio_log_folder, "read", size = "100%", qd = "1", number_to_be_tested = 16)

                # check all FIO test result
                sriov_ns_mgmt.check_fio_logs(fio_log_folder)

                logger.info("Detach NS from controllers")
                ns_amount_starter = 1
                for i in range(0, len(ns_amount_list)):
                    for k in range(ns_amount_starter, ns_amount_starter + ns_amount_list[i]):
                        if sriov_ns_mgmt.ns_detach(k, [i]) != 0:                
                            logger.error("NS Detach failed")
                            pytest.fail("NS Detach failed")
                    ns_amount_starter = ns_amount_starter + ns_amount_list[i]

            logger.info("The last step: Clear env...")
            for i in range(ns_amount, 0, -1):
                if sriov_ns_mgmt.ns_delete("/dev/nvme0", i) != 0:# delete all in decending order
                    logger.error("NS Delete failed")
                    pytest.fail("NS Delete failed")

            result = "Pass"  # if reach here, test should passed, since if fail met, pytest.fail executed
        except Exception as e:
            logger.error("Exception met during test IO on multiple NS:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))

        finally: # finally will be executed no matter what happens on try/except
            logger.info("++++Test completed: NS Capacity test, result:{}++++".format(result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("NS Capacity test: {}\n".format(result))
            
            if result == "Fail":
                logger.info("Clearing env after test execution")
                # clear env, detach all created NS and delete them after all tests 
                ns_amount_starter = 1
                for i in range(0, len(ns_amount_list)):
                    for k in range(ns_amount_starter, ns_amount_starter + ns_amount_list[i]):
                        sriov_ns_mgmt.ns_detach(k, [i], expect_fail = True)
                    ns_amount_starter = ns_amount_starter + ns_amount_list[i]
                for i in range(ns_amount, 0, -1):
                    sriov_ns_mgmt.ns_delete("/dev/nvme0", i, expect_fail = True) # delete all in decending order
                sriov_ns_mgmt.rescan_ctrl(ctrl_list)
                test_flag = -1
                pytest.fail("NS Capacity test failed")

    @pytest.mark.skip(reason="No need to test shared ns anymore as aligned with fw")
    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=1200,method="signal")
    def test_shared_ns_basic(self, vf_amount):
        '''
        1 NS shared to all 33 controllers, write on 1 NS and read on all others.
        identify nmic should be 0x1
        Create NS with non-share flag specified, and try to attach the ns to multiple controllers
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: Shared NS basic++++")
        result = "Fail"
        ctrl_list = []
        fio_log_folder = "shared_ns_basic_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        ctrl_amount = vf_amount + 1
        for i in range(0, ctrl_amount):
            ctrl_list.append(i)
        tests = sriov_ns_mgmt.ns_mgmt_basic(1) # 1 indicates shared NS
        try:
            logger.info('Create NS for test')
            for test in tests:
                controller = test['controller']
                size = hex(test['size'])  # no idea why the value here converted to int 
                capacity = hex(test['capacity'])
                flba = test['flba']
                dps = test['dps']
                shared = test['shared']
                ns_id = '1' # ns_id is 1 since only 1 created
                if sriov_ns_mgmt.ns_create(controller, size, capacity, flba, dps, shared) != 0:
                    test_flag = -1
                    pytest.fail("Create NS failed")
            ns_amount_list = sriov_ns_mgmt.spread_shared_ns_to_ctrl(1, ctrl_amount)
            attached_ns_list = []
            for i in range(0, len(ns_amount_list)):
                for k in range(1, ns_amount_list[i] + 1):
                    if sriov_ns_mgmt.ns_attach(k, [i]) != 0:
                        test_flag = -1
                        pytest.fail("Attach NS failed")
                    attached_ns_list.append("/dev/nvme{}n{}".format(i, k))
            logger.info("Attached NS list: {}".format(attached_ns_list))
            sriov_ns_mgmt.rescan_ctrl(ctrl_list)

            real_ns_list = sriov_ns_mgmt.check_get_real_ns()
            if len(attached_ns_list) != len(real_ns_list):
                test_flag = -1
                pytest.fail("Not all expected NS found, please check")

            attached_ns_list = real_ns_list  # use the actual NS list since the id might not be the same as #NO in /dev/nvme#NOn1
            logger.info("Checking nmic value of NS")
            for ns in attached_ns_list:
                if sriov_ns_mgmt.check_identify_values(ns, "nmic", '0x1') != "Passed":
                    test_flag = -1
                    pytest.fail("nmic should be 1")

            ns = attached_ns_list[random.randint(0, vf_amount)]
            logger.info("Do write on NS: {}".format(ns))
            wr_log, rd_log, rw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type="write", size="100%")

            if sriov_ns_mgmt.check_fio_result(wr_log) != "Pass":
                test_flag = -1
                logger.error("Write on shared NS failed, log file: {}".format(wr_log))
                pytest.fail("Write on shared NS failed, log file: {}".format(wr_log))

            logger.info("Do read and verify on other controllers")
            attached_ns_list.remove(ns)
            sriov_ns_mgmt.run_io_on_namespaces(attached_ns_list, fio_log_folder, "read", "100%")
            
            # check all FIO test result
            sriov_ns_mgmt.check_fio_logs(fio_log_folder)
            logger.info("The last step: Clear env...")
            for i in range(0, len(ns_amount_list)):
                for k in range(1, ns_amount_list[i] + 1):
                    if sriov_ns_mgmt.ns_detach(k, [i]) != 0:
                        logger.error("NS Detach failed")
                        pytest.fail("NS Detach failed")
            if sriov_ns_mgmt.ns_delete("/dev/nvme0", ns_id) != 0: # delete the created NS
                logger.error("NS Delete failed")
                pytest.fail("NS Delete failed")

            result = "Pass"
        except Exception as e:
            logger.error("Exception met during shared NS basic test:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))

        finally: # finally will be executed no matter what happens on try/except
            logger.info("++++Test completed: shared NS basic test, result:{}++++".format(result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("Shared NS basic: {}\n".format(result))
            
            if result == "Fail":
                test_flag = -1
                # clear env, detach and delete all NS
                logger.info("Clearing env after test execution")
                for i in range(0, len(ns_amount_list)):
                    for k in range(1, ns_amount_list[i] + 1):
                        sriov_ns_mgmt.ns_detach(k, [i], expect_fail = True)
                sriov_ns_mgmt.ns_delete("/dev/nvme0", ns_id, expect_fail = True) # delete the created NS
                sriov_ns_mgmt.rescan_ctrl(ctrl_list)
                pytest.fail("Shared NS basic test failed")

    @pytest.mark.skip(reason="No need to test shared ns anymore as aligned with fw")
    @pytest.mark.ci_nightly
    @pytest.mark.timeout(timeout=108000,method="signal")
    def test_shared_ns_capacity(self, vf_amount):
        '''
        300 NS shared to 33 controllers(1PF+32VF), write on each NS and read on others.
        '''
        global ns_mgmt_result, test_flag
        time.sleep(5)
        logger.info("++++Test start: Shared NS Capacity test++++")
        logger.info("Create 300 * 33 = 9900 NS ")
        result = 'Fail'
        ctrl_list = []
        ns_list = []
        ns_amount_list = []
        fio_log_folder = "shared_ns_capacity_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        ns_amount = 300
        ctrl_amount = vf_amount + 1
        for i in range(0, ctrl_amount):
            ctrl_list.append(i)
        for i in range(0, ns_amount):
            ns_list.append(i)
        try:
            tests = sriov_ns_mgmt.ns_mgmt_cases(ns_amount, shared_flag = 1)  # max. amount of NS, i.e. 300 NS
            if tests == -1:
                test_flag = -1
                pytest.fail("Cannot achive max capacity of device which shall be supported if NS mgmt supported, please check")
            index = 1    
            logger.info("Create NS for test")   
            for test in tests:
                logger.debug("Create NS - index: {} (start from 1)".format(index))
                controller = test['controller']
                size = test['size']
                capacity = test['capacity']
                flba = test['flba']
                dps = test['dps']
                shared = test['shared']
                if sriov_ns_mgmt.ns_create(controller, size, capacity, flba, dps, shared) != 0:
                    test_flag = -1
                    pytest.fail("Create NS failed")
                index += 1

            logger.info("300 NS on {} controller)".format(ctrl_amount))
            ns_amount_list = sriov_ns_mgmt.spread_shared_ns_to_ctrl(ns_amount, ctrl_amount)
            attached_ns_list = []
            for i in range(0, len(ns_amount_list)):
                for k in range(1, ns_amount_list[i] + 1):
                    if sriov_ns_mgmt.ns_attach(k, [i]) != 0:
                        test_flag = -1
                        pytest.fail("Attach NS failed")
                    attached_ns_list.append("/dev/nvme{}n{}".format(i, k))
            logger.debug("Attached NS list: {}".format(attached_ns_list))
           
            sriov_ns_mgmt.rescan_ctrl(ctrl_list) # rescan each controller
            ''' Due to OS can't nvme list 9900 ns, so I use Clear env to replace this, if the ns is fail, I can't clean it.
            ns_list_temp = sriov_ns_mgmt.check_get_real_ns()
            if len(attached_ns_list) != len(ns_list_temp):
                test_flag = -1
                pytest.fail("Not all expected NS found, please check")

            attached_ns_list = ns_list_temp  # use the actual NS list since the id might not be the same as #NO in /dev/nvme#NOn1
            '''
            ####### TOBE defined IO bahavior, write on each of 300 NS and read on others
            # check all FIO test result
            attached_ns_list_sample = random.sample(attached_ns_list, k = 16)
            logger.info("Due to we can't test 9900 NS and host resource limitation, random samples 16 NS to test fio. Random samples: {} )".format(attached_ns_list_sample))
            for ns in attached_ns_list_sample:
                seqwr_log, seqrd_cmd, seqrw_log = sriov_ns_mgmt.fio_on_ns(ns_str=ns, log_folder=fio_log_folder, io_type = "write_mix")
                if sriov_ns_mgmt.check_fio_result(seqrw_log) != "Pass" or sriov_ns_mgmt.check_fio_result(seqwr_log) != "Pass":
                    test_flag = -1
                    logger.error("IO on NS failed, log file: {}".format(seqrw_log))
                    pytest.fail("IO on NS failed, log file: {}".format(seqrw_log))
        
            sriov_ns_mgmt.run_io_on_namespaces(attached_ns_list_sample, fio_log_folder, "read", size = "100%", qd = "1")

            # check all FIO test result
            sriov_ns_mgmt.check_fio_logs(fio_log_folder)
            
            logger.info("The last step: Clear env...")
            for i in range(0, len(ns_amount_list)):
                for k in range(1, ns_amount_list[i] + 1):
                    if sriov_ns_mgmt.ns_detach(k, [i]) != 0:
                        logger.error("NS Detach failed")
                        pytest.fail("NS Detach failed")
            
            for i in range(ns_amount, 0, -1):
                if sriov_ns_mgmt.ns_delete("/dev/nvme0", i) != 0: # delete all in decending order
                    logger.error("NS Delete failed")
                    pytest.fail("NS Delete failed")

            result = "Pass"
        except Exception as e:
            logger.error("Exception met during test IO on multiple NS:{}".format(e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))

        finally: # finally will be executed no matter what happens on try/except
            logger.info("++++Test completed: Shared NS Capacity test, result:{}++++".format(result))
            with open(ns_mgmt_result, "a+") as f:
                f.write("Shared NS Capacity test: {}\n".format(result))
            
            if result == "Fail":
                logger.info("Clearing env after test execution")
                for i in range(0, len(ns_amount_list)):
                    for k in range(1, ns_amount_list[i] + 1):
                        sriov_ns_mgmt.ns_detach(k, [i], expect_fail = True)
                
                for i in range(ns_amount, 0, -1):
                    sriov_ns_mgmt.ns_delete("/dev/nvme0", i, expect_fail = True) # delete all in decending order
                test_flag = -1
                pytest.fail("Shared NS Capacity test failed")
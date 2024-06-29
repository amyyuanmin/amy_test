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
import time, os
import subprocess
from configparser import ConfigParser

class Test_Fct_Activate_Nvme_Cmd:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, hostname):
        global test_result, test_flag
        folder_name = hostname + "_fct_activate_nvme_cmd_logs"

        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        test_result = folder_name + '/fct_activate_nvme_cmd_result.log'

        test_flag = 0
        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        if test_flag == -1 and request.node.get_closest_marker("ci_precommit") != None:  # test for CI
            logging.error("CI test and former test failed, abort test")
            pytest.exit("Former test failed, abort test")

    @pytest.mark.ci_precommit
    @pytest.mark.ci_postcommit
    @pytest.mark.timeout(timeout=600,method="signal")
    @pytest.mark.parametrize('bs', ['4k', '256k', '260k'])
    def test_fct_activate_nvme_cmd(self, bs, pytestconfig):
        '''
        CI precommit: 4k and 260k
        CI postcommit: all
        '''
        global test_result, test_flag
        fio_log_folder = "fct_activate_nvme_cmd_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        result = "Fail"
        ci_scenario = pytestconfig.getoption('-m')

        if ci_scenario == "ci_precommit" and bs == "256k":
            pytest.skip("CI Precommit, skip 256k test")

        try:
            if bs == "4k":
                io_log = self.fio_runner(bs, "precondition", fio_log_folder)
                if self.check_fio_result(io_log) != "Pass":
                    logging.error("Write failed, log file: {}".format(io_log))
                    pytest.fail("Write failed, log file: {}".format(io_log))
            
            io_log = self.fio_runner(bs, "read", fio_log_folder)
            if self.check_fio_result(io_log) != "Pass":
                logging.error("Read failed, log file: {}".format(io_log))
                pytest.fail("Read failed, log file: {}".format(io_log))

            result = "Pass"

        except Exception as e:
            logging.error("FCT activate nvme cmd test failed:{}".format(e))
            logging.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
        finally:
            with open(test_result, "a+") as f:
                f.write("fct_activate_nvme_cmd_{}: {}\n".format(bs, result))

            if result == "Fail":
                test_flag = -1
                pytest.fail("Test fct_activate_nvme_cmd_{} failed".format(bs))


    def fio_runner(self, bs, section, log_folder = os.getcwd()):
        '''
        bs: block size for test, if size defined in .fio
        section: precommit_write or other tests
        '''
        io_cfg = self.parse_config("io_cfg")
        
        if section == "precondition":
            section = "precondition_write"
            io_log = os.path.join(log_folder, "precondition_write")
        else:
            section = "seqrd"
            io_log = os.path.join(log_folder, "seqrd_{}.log".format(bs))

        io_cmd = "sudo BS={} fio {} --section={} --output={}".format(bs, io_cfg, section, io_log)

        timeout = int(self.parse_config("timeout"))
        
        self.execute_cmd(io_cmd, timeout)

        return io_log

    def parse_config(self, item):
        config_file = "./fct_activate_nvme_cmd_cfg.txt"
        config = ConfigParser()
        config.read(config_file)

        item_value = config.get('fct_activate_nvme_cmd', item).strip()
        if "," in item_value:
            item_value = item_value.split(",")
        
        return item_value

    def check_fio_result(self, log_file, pattern = "err="):
        logging.info("Checking fio result: {}".format(log_file))
        result = 'Pass'
        flag = 0  # if no err= info in output file
        if os.path.exists(log_file):
            with open(log_file, 'r') as processLog:
                while True:
                    entry = processLog.readline()
                    if pattern in entry:
                        flag = 1
                        if pattern + " 0" in entry:
                            logging.info("FIO test passed")
                            result = "Pass"  # there might be several result, for ex. Mixed RW
                        else:
                            logging.info("FIO test failed")
                            result = "Fail"
                            break
                    elif entry == '':
                        if flag == 0:
                            logging.info("No result info found, FIO test failed")
                            result = "Fail"
                        break
        else:
            logging.error("No fio log found:{}".format(log_file))
            result = "Fail"
        return result


    def execute_cmd(self, cmd, timeout, out_flag = False, expect_fail = False, expect_err_info = None):
        '''
        Execute cmd in #timeout seconds
        out_flag: True means return cmd out(a str list), Flase not.
        expect_fail: for some error inject scenario, set this to True
        expect_err_info: if expect failure, then check the error msg as expected or not
        '''
        logging.info(cmd)
        result = 0
        try:
            p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell = True) 
            t_beginning = time.time()
            seconds_passed = 0 
            while True:
                if p.poll() is not None: 
                    out = p.stdout.readlines()
                    out = [i.decode().strip("\n") for i in out]  # convert to string
                    if p.returncode == 0:
                        logging.info("Cmd executed successfully")
                    elif p.returncode != 1:  # specified scenario: nvme list | grep nvme, if nothing returned, the returncode is 1, it seems caused by the grep, for ex. ls | grep leon, if nothing found, returncode is 1
                        logging.info("Cmd output: {}".format(out[0]))  # just show the first out to avoid too many logs
                        if expect_fail:
                            logging.info("Cmd executed failed, but it's as expected")
                            result = 0
                            if expect_err_info != None and expect_err_info not in out[0]:
                                logging.warning("Error msg not as expected, you may have a check")
                        else:
                            logging.error("Cmd executed failed")
                            result = -1
                    break 
                time.sleep(1)
                seconds_passed = time.time() - t_beginning 
                if seconds_passed > timeout: 
                    p.stdout.close()
                    if "fio" in cmd:
                        os.system("pkill -9 fio")
                    p.terminate()
                    logging.info('Cmd not end as expected in {} seconds, terminate it'.format(timeout))
                    result = -1
                    break
            p.stdout.close()
        except Exception as e:
            logging.error("Cmd execution failed: {}".format(e))
            result = -1
        if out_flag == False:
            return result
        else:
            return result, out
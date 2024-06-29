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
from fvt_adm_cmd_common import fvt_adm
import multi_chunk_util
import sys
sys.path.append("../")
from common import util

class Test_Multi_Chunk:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, controller, namespace, hostname):
        global multi_chunk_result, adm_common, test_flag
        folder_name = hostname + "_multi_chunk_logs"

        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        multi_chunk_result = folder_name + '/multi_chunk_result.log'
        
        adm_common = fvt_adm(controller, namespace)
        test_flag = 0
        yield
        os.system("cp -r *fio_logs {}".format(log_folder))  # collect FIO logs for each test, each test has individual log folder
        os.system("rm -fr *fio_logs")

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        if test_flag == -1 and request.node.get_closest_marker("ci_postcommit") != None:  # test for CI
            logging.error("CI test and former test failed, abort test")
            pytest.exit("Former test failed, abort test")

    @pytest.mark.ci_precommit
    @pytest.mark.ci_postcommit
    @pytest.mark.timeout(timeout=600,method="signal")
    @pytest.mark.parametrize('scenario', ['128k_divisible', '128k_nondivisible'])
    def test_multi_chunk(self, scenario, build, pytestconfig):
        '''
        Steps:
        1. Write, 2. Read verify
        Two scenario:
        1. fio block size can be divided by 128k(test range 0 - 50%)
        2. fio block size can not be divided by 128k(test range 50% - 100%)
        '''
        global multi_chunk_result, test_flag
        fio_log_folder = "multi_chunk_io_basic_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        result = "Fail"
        ns = "/dev/nvme0n1"

        ci_scenario = pytestconfig.getoption('-m')
        if ci_scenario == "ci_precommit" and scenario == "128k_nondivisible":
            pytest.skip("CI Precommit, skip 128k_nondivisible test")
            
        try:
            mdts = multi_chunk_util.parse_config("mdts")
            id_data = adm_common.ctrl_identify()
            if id_data.mdts == int(mdts): # 2 ^ 9 x 4k = 2048k
                logging.info("MDTS check passed")
            else:
                logging.error("MDTS check failed, expected: {}".format(mdts))
                pytest.fail("MDTS check failed, expected: {}".format(mdts))
            
            if build == "E2e":
                if scenario == "128k_divisible":
                    offset_tmp = 0
                if scenario == "128k_nondivisible":
                    offset_tmp = "50%"
                size = "50%"
            elif build == "Ramdrive":
                offset_tmp = 0
                size = "100%"
            io_size_list = multi_chunk_util.parse_config(scenario)
            wr_log, rw_log, rd_log = multi_chunk_util.fio_on_ns(ns, offset = offset_tmp, size = size, log_folder = fio_log_folder, io_type = "write", bs = io_size_list[0], test = "basic")
            if multi_chunk_util.check_fio_result(wr_log) != "Pass":
                logging.error("Write failed, log file: {}".format(wr_log))
                pytest.fail("Write failed, log file: {}".format(wr_log))

            for io_size in io_size_list[1:]:
                wr_log, rw_log, rd_log = multi_chunk_util.fio_on_ns(ns, offset = offset_tmp, size = size, log_folder = fio_log_folder, io_type = "read", bs = io_size.strip(), test = "basic")
                if multi_chunk_util.check_fio_result(rd_log) != "Pass":
                    logging.error("Read verify failed, log file: {}".format(rd_log))
                    pytest.fail("Read verify failed, log file: {}".format(rd_log))
            
            result = "Pass"

        except Exception as e:
            logging.error("Multi_chunk test failed:{}".format(e))
        finally:
            with open(multi_chunk_result, "a+") as f:
                f.write("multi_chunk_{}: {}\n".format(scenario, result))

            if result == "Fail":
                test_flag = -1
                pytest.fail("Test multi_chunk_{} failed".format(scenario))

    @pytest.mark.ci_postcommit
    @pytest.mark.timeout(timeout=1200,method="signal")
    def test_multi_chunk_stress(self, build):
        '''
        Step:
        1. Write to 0% - 50%
        2. Mixed RW, read 0% - 50%, write 50% - 100%
        '''
        global multi_chunk_result, test_flag
        fio_log_folder = "multi_chunk_stress_fio_logs"
        if not os.path.exists(fio_log_folder):
            os.mkdir(fio_log_folder)
        result = "Fail"
        ns = "/dev/nvme0n1"
        try:
            util.nvme_format(format_lbaf="1")
            if build == "E2e":
                offset_write = "0"
                offset_mix_rw = "50%"
                test_size = "50%"
            elif build == "Ramdrive":
                offset_write = "0%"
                offset_mix_rw = "0%"
                test_size = "100%"

            io_size_list = multi_chunk_util.parse_config("stress")
            wr_log, rw_log, rd_log = multi_chunk_util.fio_on_ns(ns, offset = offset_write, size = test_size, log_folder = fio_log_folder, io_type = "write", bs = io_size_list[0], test = "stress")
            if multi_chunk_util.check_fio_result(wr_log) != "Pass":
                logging.error("Write failed, log file: {}".format(wr_log))
                pytest.fail("Write failed, log file: {}".format(wr_log))

            wr_log, rw_log, rd_log = multi_chunk_util.fio_on_ns(ns, offset = offset_mix_rw, size = test_size, log_folder = fio_log_folder, io_type = "mix", bs = io_size_list[1], test = "stress")
            if multi_chunk_util.check_fio_result(rw_log) != "Pass":
                logging.error("Read verify failed, log file: {}".format(rw_log))
                pytest.fail("Read verify failed, log file: {}".format(rw_log))
            
            result = "Pass"

        except Exception as e:
            logging.error("Multi_chunk stress test failed:{}".format(e))
        
        finally:
            with open(multi_chunk_result, "a+") as f:
                f.write("multi_chunk_stress: {}\n".format(result))

            if result == "Fail":
                test_flag = -1
                pytest.fail("Test multi_chunk_stress failed")


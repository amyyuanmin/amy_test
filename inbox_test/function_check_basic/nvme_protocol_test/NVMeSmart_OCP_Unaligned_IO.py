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

import logging
import time
import subprocess
import random
from sfvs.nvme import nvme
from sfvs.nvme.utils import Utils as utils
from nvme_protocol_test.fvt_adm_cmd_common import fvt_adm
from nvme_protocol_test.fvt_io_cmd_common import fvt_io
from nvme_protocol_test.smart_lib import SMART

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')

def NVMeSmart_OCP_Unaligned_IO(ns_data, ctrl, ns, result_file):
    result = "FAILED"

    results_dict = {}
    finalResult = []
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    try:
        # Get the Unaligned_IO from Smart before Unligned IO
        Unaligned_IO_before=int(smart.smart_OCP_vendor("Unaligned_IO"))
        logging.info("Unaligned_IO before Unligned IO =   {}".format(Unaligned_IO_before))

        # FIO unaligned IO write
        # Need to sync with Fw team about how many bytes aligned

        verify_pattern = "".join([random.choice("0123456789ABCDEF") for p in range(8)])
        test_flag = run_fio_param(offset="1k", rw="write_unaligned", bs="4k", Qdepth="32", pattern=verify_pattern,size="128M", verify="1")
        if test_flag == -1:
            logging.error("check write unaligned result fail")

        # Get the Unaligned_IO from Smart after Unligned IO
        Unaligned_IO_after=int(smart.smart_OCP_vendor("Unaligned_IO"))
        logging.info("Unaligned_IO after Unligned IO =   {}".format(Unaligned_IO_after))

        if Unaligned_IO_after > Unaligned_IO_before:
            result = "PASSED"

    except Exception as e:
        logging.error("Not Working with Error: {}".format(str(e)))

    with open("{}/OCP_Smart_result.log".format(result_file), 'a+') as f:
        f.write("NVMeSmart_OCP_Unaligned_IO         {} \n".format(result))
        f.close()
    return result

def generate_io_cmd(offset, rw, bs, Qdepth, pattern, size, runtime="0", verify="0"):
    '''
        :param
        rw: read, write, randread, randwrite, randread_unaligned
        bs: 4k, 8k, 32k, 64k, 128k
        Qdepth: 1,8, 16, 32, 64
        size: range size
        runtime: s
        :return: fio result
        '''
    if runtime != "0":
        time_based = " --time_based --runtime={}".format(runtime)
    else:
        time_based = ""
    if verify == "1":
        verify_cmd = " --do_verify=1 --verify_dump=1 --verify_fatal=1 --verify_backlog=1"
    else:
        verify_cmd = " --do_verify=0"
    fio_log = "fio_" + rw + ".log"

    if rw == "randread_unaligned":
        cmd = "sudo fio --name={} --offset={} --ioengine=libaio --direct=1 --buffered=0 --size={} --continue_on_error=0 --bs={}--iodepth={} --verify_pattern=0x{} --verify=meta --rw=randread --filename=/dev/nvme0n1 --output={}{}{}".format(rw, offset, size, bs, Qdepth, pattern, fio_log, time_based, verify_cmd)
    elif rw == "write_unaligned":
        cmd = "sudo fio --name={} --offset={} --ioengine=libaio --direct=1 --buffered=0 --size={} --continue_on_error=0 --bs={} --iodepth={} --verify_pattern=0x{} --verify=meta --rw=write --filename=/dev/nvme0n1 --output={}{}{}".format(rw, offset, size, bs, Qdepth, pattern, fio_log, time_based, verify_cmd)
    else:
        cmd = "sudo fio --name={} --offset={} --ioengine=libaio --direct=1 --buffered=0 --size={} --continue_on_error=0 --bs={} --iodepth={} --verify_pattern=0x{} --verify=meta --rw={} --filename=/dev/nvme0n1 --output={}{}{}".format(rw, offset, size, bs, Qdepth, pattern, rw, fio_log, time_based, verify_cmd)
    return cmd,fio_log

def run_fio(runtime,cmd):
    p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    t_beginning = time.time()
    result = -1
    timeout = 70
    while True:
        if p.poll() is not None:
            logging.info(" FIO test is done.")
            break
        time.sleep(5)
        seconds_passed = time.time() - t_beginning
        if seconds_passed > int(timeout) + int(runtime):
            p.terminate()
            logging.error("check write unaligned result fail")

def run_fio_param(offset, rw, bs, Qdepth, pattern, size, runtime="0", verify="0"):
    cmd,fio_log = generate_io_cmd(offset, rw, bs, Qdepth, pattern, size, runtime=runtime, verify=verify)
    logging.info(cmd)
    run_fio(runtime,cmd)
    test_flag = fio_verify(fio_log)
    return test_flag


def fio_verify(fio_log):
    flag = -1
    with open(fio_log, 'r') as processLog:
        while True:
            entry = processLog.readline()
            if "err=" in entry:
                if "err= 0" in entry:
                    result = 0
                    logging.info(entry.strip())
                    logging.info(" Check FIO: pass")
                    flag = 0
                    break
                else:
                    logging.info(" Check FIO: fail")
                    break
            elif entry == '':
                break
    return flag




def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###########################################################################")
    logging.info("#                       NVMeSmart_OCP_Unaligned_IO                        #")
    logging.info("###########################################################################")

    return NVMeSmart_OCP_Unaligned_IO(ns_data, ctrl, ns, result_file)
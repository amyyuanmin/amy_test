#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2081 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2018 Marvell Semiconductor.
#
# Version Control Information:
#
#
#  $Id$
#  revision: 0.1
#
#  Author:  Leon Cheng
#
#  Oct. 16, 2020
#####################################################################################################################

import time
import pytest
import logging
from nvme import Controller, Namespace, Buffer, Qpair, Pcie, Subsystem
import os


def test_download_during_IO(nvme0, nvme0n1, pcie, loop, verify): 
    # assert verify
    region_end = 256*1000*200000  # 100GB
    iosz_distribution = [1, 2, 8, 16, 32, 64, 128, 256]
    logging.info("Issue 50%-50% random read/write IO")
    
    for i in range(int(loop)):
        logging.info("Loop: {}".format(i))
        cmdlog_list = [None]*1000
        with nvme0n1.ioworker(io_size=iosz_distribution,
                            lba_random=True,
                            read_percentage=50,
                            region_end=region_end,
                            time=40,  
                            qdepth=256,
                            output_cmdlog_list=cmdlog_list):
            time.sleep(10)
            
            if (i % 2 == 0):
                nvme0.downfw('target2.sdfw', 0, 3)
            else:
                nvme0.downfw('target1.sdfw', 0, 3)
            time.sleep(10)
            # logging.info("Rescan and controller reset to detect device")
            # pcie.reset(rst_fn=rst_fn)
            # nvme0.reset()
        # verify data in cmdlog_list
        assert True == nvme0n1.verify_enable(True)
        logging.info(cmdlog_list[-10:])
        read_buf = Buffer(256 * 512)
        qpair = Qpair(nvme0, 10)   # one note: issue #1, if not define here, error reported
        for cmd in cmdlog_list:
            slba = cmd[0]
            nlba = cmd[1]
            op = cmd[2]
            if nlba and op==1:
                def read_cb(cdw0, status1):
                    nonlocal slba
                    if status1>>1:
                        logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
                nvme0n1.read(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
                # re-write to clear CRC mismatch
                nvme0n1.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
        qpair.delete()

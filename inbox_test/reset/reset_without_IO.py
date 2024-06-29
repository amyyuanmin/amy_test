#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2022 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2022 Marvell Semiconductor.
#
# Version Control Information:
#
#
#  $Id$
#  revision: 0.1
#
#  Author:  Leon Cheng
#
#  May. 6, 2020
#####################################################################################################################

'''
Input from conftest:
loop - how many loops test run
pciaddr - pci(BDF) address of the DUT
ns_id - NS id for test, basically used to issue IO during test
'''
import time
import pytest
import logging
from nvme import Pcie, Controller, Subsystem, Namespace
import reset_util

@pytest.fixture(scope='session', autouse=True)
def setup_teardown(pciaddr, ns_id):
    global pcie, controller, subsystem, namespace, namespace_id
    '''
    Initialize objects before test, including pcie, controller, namespace, subsystem, etc
    '''
    pcie = Pcie(pciaddr)
    controller = Controller(pcie)
    subsystem = Subsystem(controller)
    namespace_id = int(ns_id)
    namespace = Namespace(controller, namespace_id)    
    assert namespace.verify_enable(True)
    yield 
    namespace.close()
    
def test_controller_reset_without_io(loop):
    reset_without_io(pcie, controller, namespace, subsystem, reset_util.controller_reset, loop)

def test_subsystem_reset_without_io(loop):
    reset_without_io(pcie, controller, namespace, subsystem, reset_util.subsystem_reset, loop)

def test_pcie_hot_reset_without_io(loop):
    reset_without_io(pcie, controller, namespace, subsystem, reset_util.pcie_hot_reset, loop)

def test_flr_without_io(loop):
    reset_without_io(pcie, controller, namespace, subsystem, reset_util.flr, loop)

def reset_without_io(pcie, ctrl, ns, subs, reset_fun, loop): 
    '''
    Region should be adjusted due to performance
    Step1. Write 10G
    Step2. Mixed IO with Read 10G + Write 30G
    '''
    region_end_write = 256*1024*10  # 10GB
    region_end_mix = 256*1024*40 # 40GB
    cmdlog_list = [None]*1000
    delay = 10
    pvalue = 0x55aa55aa
        
    lba_size = 4 # default LBAF is 4k
    io_size_list = [1, 8, 32] # 4k, 32k, 128k, not consider multi-chunk as aligned with fw
    q_depth_list = [4, 16, 64, 256, 512]
    index = 0
    for i in range(0, int(loop)//(len(io_size_list)*len(q_depth_list)) + 1): 
        for io_size in io_size_list: # 4k, 32k, 128k, not consider multi-chunk as aligned with fw
            for q_depth in q_depth_list:
                logging.info("########Loop: {}########".format(index))
                logging.info("Step 1. Write for {}s".format(delay))
                ns.ioworker(io_size=32,  # unit is lba
                            lba_random=False,
                            read_percentage=0,
                            ptype=32,
                            pvalue=pvalue,
                            time=delay,
                            region_end=region_end_write,
                            qdepth=512).start().close()
                logging.info("Step 2. Issue Mixed IO for {}s, Read 10G + Write 30G, io_size={}, q_depth={}".format(delay, io_size * lba_size, q_depth))
                ioworkers=[]
                worker1 = ns.ioworker(io_size=io_size,
                            lba_random=False,
                            read_percentage=0,
                            region_start=region_end_write,
                            region_end=region_end_mix,
                            time=delay,
                            ptype=32,
                            pvalue=pvalue,
                            qdepth=q_depth,
                            output_cmdlog_list=cmdlog_list).start()
                ioworkers.append(worker1)
                worker2 = ns.ioworker(io_size=io_size,
                            lba_random=False,
                            read_percentage=100,
                            region_end=region_end_write,
                            time=delay,
                            ptype=32,
                            pvalue=pvalue,
                            qdepth=q_depth,
                            output_cmdlog_list=cmdlog_list).start()
                ioworkers.append(worker2)
                for worker in ioworkers:
                    worker.close()  #Wait the ioworker's process finish
                time.sleep(2)
                logging.info('Step 3. Issue reset after IO')
                reset_fun(ctrl, pcie, subs)  # issue reset     
                ctrl.getfeatures(7).waitdone()  # an admin cmd after reset        

                # logging.info(cmdlog_list[-10:])
                # read_buf = Buffer(256 * 512)
                # qpair = Qpair(ctrl, 10)   # one note: issue #1, if not define here, error reported
                # for cmd in cmdlog_list:
                #     slba = cmd[0]
                #     nlba = cmd[1]
                #     op = cmd[2]
                #     if nlba and op==1:
                #         def read_cb(cdw0, status1):
                #             nonlocal slba
                #             if status1>>1:
                #                 logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
                #         ns.read(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
                #         # re-write to clear CRC mismatch
                #         ns.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
                # qpair.delete()
                
                logging.info("Step 4. Format drive")
                ctrl.format(lbaf=1, ses=0, nsid=namespace_id).waitdone()
                time.sleep(2)
                index += 1
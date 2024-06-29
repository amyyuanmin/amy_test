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

import time
import pytest
import logging
from nvme import Pcie, Controller, Subsystem, Namespace
import reset_util
import threading
import sys
sys.path.append("../")
from common import util

# Basic rule: one NS on each function. 
# As aligned Currently only test 16 PFs for Multi-PF, i.e. ARI not enabled.
# 64 PFs support if ARI enabled, Will enable this scenario later.
@pytest.fixture(scope='session', autouse=True)
def setup_teardown(func_amount):
    global pcie_addr_list, pcie_list, ctrl_list, subsystem, ns_list, ns_id_list, capacity
    '''
    Initialize objects before test, including pcie, controller, namespace, subsystem, etc
    '''
    capacity = 256*1024*5 # capacity of each NS, set default to 5G, so that ns create/attach process can be ignore for debug purpose
    func_amount = int(func_amount)
    pcie_addr_list = util.get_pci_addr_list()[:func_amount]  # might not use all available NS for testing
    pcie_list = []
    ctrl_list = []
    ns_list = []
    ns_id_list = []
    for pciaddr in pcie_addr_list:
        index = pcie_addr_list.index(pciaddr)
        namespace_id = index + 1  # One NS on each function
        logging.info("Initialization for {}, ns id:{}".format(pciaddr, namespace_id))
        pcie = Pcie(pciaddr)
        controller = Controller(pcie)
        if index == 0:
            subsystem = Subsystem(controller) # Due to the latest design, only one subsystem exists 
            # comment two lines below if no need to create NS
            capacity = reset_util.get_ns_capacity(controller, func_amount)
        reset_util.ns_setup(controller, namespace_id, capacity)
        namespace = Namespace(controller, namespace_id)  
        pcie_list.append(pcie)
        ctrl_list.append(controller)
        ns_list.append(namespace)
        ns_id_list.append(namespace_id)
    time.sleep(60) # It takes quite a lot of time for fw to finish all actions above.
    yield 
    for index in range(0, len(pcie_addr_list)):
        ns_list[index].close()
        pcie_list[index].close()

@pytest.mark.reset
def test_normal_ctrl_reset_multi_pf(loop):
    reset_multi_pf(reset_without_io, reset_util.controller_reset, loop)

@pytest.mark.leon
def test_interrupt_ctrl_reset_multi_pf(loop):
    reset_multi_pf(reset_during_io, reset_util.controller_reset, loop)

@pytest.mark.reset
def test_normal_nssr_multi_pf(loop):
    reset_multi_pf(reset_without_io, reset_util.subsystem_reset, loop)

@pytest.mark.reset
def test_interrupt_nssr_multi_pf(loop):
    reset_multi_pf(reset_during_io, reset_util.subsystem_reset, loop)

@pytest.mark.reset
def test_normal_flr_multi_pf(loop):
    reset_multi_pf(reset_without_io, reset_util.flr, loop)

@pytest.mark.reset
def test_interrupt_flr_multi_pf(loop):
    reset_multi_pf(reset_during_io, reset_util.flr, loop)
  
@pytest.mark.reset  
def test_normal_pci_hot_reset_multi_pf(loop):
    reset_multi_pf(reset_without_io, reset_util.pcie_hot_reset, loop)

@pytest.mark.reset
def test_interrupt_pci_hot_reset_multi_pf(loop):
    reset_multi_pf(reset_during_io, reset_util.pcie_hot_reset, loop)
    
# Note: Too many params required if put below functions to lib(reset_util.py). So not.
def reset_multi_pf(scenario, reset_fun, loop):
    '''
    scenario: reset_without_io or reset_during_io
    '''
    global overall_result
    io_size_list = [1, 8, 32] # 4k, 32k, 128k, not consider multi-chunk as aligned with fw
    q_depth_list = [4, 16, 64, 256, 512]
    loop_index = 0
    for i in range(0, int(loop)//(len(io_size_list)*len(q_depth_list)) + 1): 
        for io_size in io_size_list: # 4k, 32k, 128k, not consider multi-chunk as aligned with fw
            for q_depth in q_depth_list:
                overall_result = []  # used to record the overall result of test. Workaround for result check with threading. There should be func_amount results in this list.
                logging.info("########Loop: {} - io_size:{},q_depth:{}########".format(loop_index, io_size, q_depth))
                logging.info("Step 0. Format drive")
                # For SDK, Format at backend for the whole drive, not function/NS specified. 
                # If there's write in progress when format, data also be formated.
                ctrl_list[0].format(lbaf=1, ses=0).waitdone()
                thread_list = []
                for pcie in pcie_list:
                    index = pcie_list.index(pcie)
                    t = threading.Thread(target=scenario, args=(pcie, ctrl_list[index], ns_list[index], subsystem, reset_fun, index, io_size, q_depth))
                    t.start()
                    thread_list.append(t)
                for t in thread_list:
                    t.join(timeout = 300)
                if len(overall_result) != int(len(pcie_addr_list)):
                    logging.info("Tests passed on Func: {}".format(overall_result))
                    logging.error("Not tests on all func passed.")
                    pytest.fail("Not tests on all func passed.")
                loop_index += 1
    
def reset_without_io(pcie, ctrl, ns, subs, reset_fun, index, io_size, q_depth): 
    '''
    index: used to randomize delay for different thread to avoid reset at the same time
    Region should be adjusted due to performance
    Step1. Write 1/5 of NS
    Step2. Mixed IO with Read 1/5 of NS + Write 2/5 NS
    '''
    global overall_result
    # region_end_write = capacity // 5 
    # region_end_mix = capacity * 4 // 5
    region_end_write = 256 * 1024
    region_end_mix = 256 * 1024 * 4
    cmdlog_list = [None]*1000
    delay = 10
    pvalue = 0x55aa55aa
    lba_size = 4 # default LBAF is 4k
    time.sleep(0.1 * index)
    try:
        logging.info("{} - Step 1. Write for {}s".format(pcie_addr_list[index], delay))
        ns.ioworker(io_size=32,  # unit is lba
                    lba_random=False,
                    read_percentage=0,
                    ptype=32,
                    pvalue=pvalue,
                    time=delay,
                    region_end=region_end_write,
                    qdepth=512).start().close()
        logging.info("{} - Step 2. Issue Mixed IO for {}s, io_size={}, q_depth={}".format(pcie_addr_list[index], delay, io_size * lba_size, q_depth))
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
        if index != 0 and reset_fun == reset_util.pcie_hot_reset:
            logging.info("{} - Ignore Step 3, PCI Hot Reset issued only on one PF(PF0)".format(pcie_addr_list[index]))
        else:
            logging.info('{} - Step 3. Issue reset after IO'.format(pcie_addr_list[index]))
            reset_fun(ctrl, pcie, subs)  # issue reset     
        # ctrl.getfeatures(7).waitdone()  # No need this, identify and set feature already included in reset process
        time.sleep(1)
        overall_result.append(index) # Equal to Function ID. If fail met, scripts won't run to here
    except:
        pass

def reset_during_io(pcie, ctrl, ns, subs, reset_fun, index, io_size, q_depth): 
    '''
    index: used to randomize delay for different thread to avoid reset at the same time
    Region should be adjusted due to performance
    Step1. Write 1/5 of NS
    Step2. Mixed IO with Read 1/5 of NS + Write 2/5 NS
    '''
    global overall_result
    # region_end_write = capacity // 5 
    # region_end_mix = capacity * 4 // 5
    region_end_write = 256 * 1024
    region_end_mix = 256 * 1024 * 4
    cmdlog_list = [None]*1000
    delay = 10
    pvalue = 0x55aa55aa
    lba_size = 4 # default LBAF is 4k
    time.sleep(0.1 * index)
    try:
        logging.info("{} - Step 1. Write for {}s".format(pcie_addr_list[index], delay))
        ns.ioworker(io_size=32,  # unit is lba
                    lba_random=False,
                    read_percentage=0,
                    ptype=32,
                    pvalue=pvalue,
                    time=delay,
                    region_end=region_end_write,
                    qdepth=512).start().close()
        logging.info("{} - Step 2. Issue Mixed IO for {}s, io_size={}, q_depth={}".format(pcie_addr_list[index], delay, io_size * lba_size, q_depth))
        # with statement should be used, otherwise ioworker won't be handled correctly after reset
        with ns.ioworker(io_size=io_size,
                    lba_random=False,
                    read_percentage=0,
                    region_start=region_end_write,
                    region_end=region_end_mix,
                    ptype=32,
                    pvalue=pvalue,
                    time=(delay * 2),
                    qdepth=q_depth,                    
                    output_cmdlog_list=cmdlog_list):
            with ns.ioworker(io_size=io_size,
                        lba_random=False,
                        read_percentage=100,
                        region_end=region_end_write,
                        ptype=32,
                        pvalue=pvalue,
                        time=(delay * 2),
                        qdepth=q_depth,
                        output_cmdlog_list=cmdlog_list):
                time.sleep(delay)
                if index != 0 and reset_fun == reset_util.pcie_hot_reset:
                    logging.info("{} - Ignore Step 3, PCI Hot Reset issued only on one PF(PF0)".format(pcie_addr_list[index]))
                else:
                    logging.info('{} - Step 3. Issue reset during IO after delay {}s'.format(pcie_addr_list[index], delay))
                    reset_fun(ctrl, pcie, subs)  # issue reset       
        
        time.sleep(1)
        overall_result.append(index) # Equal to Function ID. If fail met, scripts won't run to here
    except:
        pass

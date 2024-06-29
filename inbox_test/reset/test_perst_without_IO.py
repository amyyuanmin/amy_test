# -*- coding: utf-8 -*-

import time, os
import random
import pytest
import logging
import quarchpy
from quarchpy.device import *
from nvme import Pcie, Controller, Subsystem, Namespace, Buffer, Qpair

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
    yield pcie, controller
    namespace.close()
    
@pytest.fixture(scope='function')
def device(setup_teardown):
     # If not a PPM
    if os.path.exists("/dev/ttyUSB0"):
        logging.info("Start Quarch connection")
        device = quarchpy.quarchDevice("SERIAL:/dev/ttyUSB0")
    else:
        try:
            # get available devices, output: {'USB:QTL1999-05-041': 'QTL1999-05-041'}
            currentDevices = scanDevices()
            if len(currentDevices) == 0:
                pytest.fail("No available quarch device found")
            else:
                print("Available quarch device: {}".format(currentDevices))
        except Exception as e:
            pytest.fail("Failed to get quarch power module list:{}".format(e))

        myDeviceID = ""
        for key in currentDevices:
            if 'USB' in key:
                myDeviceID = key
        if myDeviceID == "":
            pytest.fail("No available quarch device found")

        logging.info("Start Quarch connection")
        device = quarchpy.quarchDevice(myDeviceID)
        
    # PERST issued during initial quarchDevice, thus pynmve need to rescan the device
    pcie, controller = setup_teardown
    logging.info("Rescan by pynvme")
    pcie.reset()
    controller.reset()
    
    yield device

    device.closeConnection()

def quarch_perst(delay, device, glitch):
    '''
    Issue PERST via quarch at specified glitch
    '''
    glitch_mapping = {"120ms": "5ms 24"}
    logging.info("Wait {}s and issue PERST".format(delay))
    time.sleep(delay)
    logging.info("PERST by Quarch with {} glitch".format(glitch))
    device.sendCommand("SIGnal:PERST:GLITch:ENAble ON")
    device.sendCommand("GLITch:SETup {}".format(glitch_mapping[glitch]))  
    device.sendCommand("SIGnal:PERST:DRIve:OPEn LOW")
    device.sendCommand("RUN:GLITch ONCE")

def test_perst_without_io(device, loop):   
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
                logging.info("Step 1. Write for {}s".format(delay * 2))
                namespace.ioworker(io_size=32,  # unit is lba
                            lba_random=False,
                            read_percentage=0,
                            ptype=32,
                            pvalue=pvalue,
                            region_end=region_end_write,
                            time=(delay * 2),
                            qdepth=512).start().close()
                logging.info("Step 2. Issue Mixed IO for {}s, Read 10G + Write 30G, io_size={}, q_depth={}".format(delay, io_size * lba_size, q_depth))
                ioworkers=[]
                worker1 = namespace.ioworker(io_size=io_size,
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
                worker2 = namespace.ioworker(io_size=io_size,
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
                    
                logging.info('Step 3. Issue PERST after IO') 
                flag = random.randint(0, 1000)        
                if flag % 2 == 0:
                    logging.info("Glitch: 120ms")
                    glitch = "120ms"
                else:
                    logging.info("Glitch: 120ms")
                    glitch = "120ms"
                quarch_perst(2, device, glitch)
                pcie.reset(rst_fn=rst_fn)
                controller.reset()
                
                # logging.info(cmdlog_list[-10:])
                # read_buf = Buffer(256 * 512)
                # qpair = Qpair(controller, 10)   # one note: issue #1, if not define here, error reported
                # for cmd in cmdlog_list:
                #     slba = cmd[0]
                #     nlba = cmd[1]
                #     op = cmd[2]
                #     if nlba and op==1:
                #         def read_cb(cdw0, status1):
                #             nonlocal slba
                #             if status1>>1:
                #                 logging.info("slba 0x%x, status 0x%x" % (slba, status1>>1))
                #         namespace.read(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
                #         # re-write to clear CRC mismatch
                #         namespace.write(qpair, read_buf, slba, nlba, cb=read_cb).waitdone()
                # qpair.delete()
                
                logging.info("Step 4. Format drive")
                controller.format(lbaf=1, ses=0, nsid=namespace_id).waitdone()
                time.sleep(2)
                index += 1

def rst_fn():
    pass
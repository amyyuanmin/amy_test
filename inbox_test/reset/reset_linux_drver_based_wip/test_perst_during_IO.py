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

import time, os
import random
import pytest
import logging
import quarchpy
from quarchpy.device import *
import threading

@pytest.fixture(scope='function')
def device():
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

def test_perst_during_io(device, loop):   
    logging.info("Prefill the drive")
    pci_addr_list = util.get_pci_addr_list()
    util.remove_device(pci_addr_list[0])
    util.rescan_device()   
    
    io_size_list = ["4k", "32k", "128k"] # 4k, 32k, 128k, not consider multi-chunk as aligned with fw
    q_depth_list = [2, 8, 32, 128, 256]  # half for read, half for write
    
    index = 0
    for i in range(0, int(loop)//(len(io_size_list)*len(q_depth_list))): 
        for io_size in io_size_list: # 4k, 32k, 128k, not consider multi-chunk as aligned with fw
            for q_depth in q_depth_list:
                logging.info("###Loop: {}, io_size: {}, q_depth: {}###".format(index, io_size, q_depth))
                logging.info("Prefill 20% of drive")
                fio_runner(io_type="write", bs="128k", q_depth=128, offset=0, size="20%", timeout=180) 
                flag = random.randint(0, 1000)
                logging.info('flag: {}'.format(flag))

                if flag % 2 == 0:
                    glitch = "120ms"
                else:
                    glitch = "120ms"       
                t_list = []
                t0 = threading.Thread(target=fio_runner, args=("write",io_size, q_depth, "20%", "80%", 15,))
                t0.start()
                t1 = threading.Thread(target=fio_runner, args=("read",io_size, q_depth, "0", "20%", 15, 15,))
                t1.start()
                t2 = threading.Thread(target=quarch_perst, args=(10, device, glitch,))        
                t2.start()
                t_list.append(t0)
                t_list.append(t1)
                t_list.append(t2)

                for t in t_list:
                    t.join() 
                    
                os.system("pkill -9 fio")
                
                util.remove_device(pci_addr_list[0])
                util.rescan_device()
                time.sleep(2)
                lbaf = "1"
                ns_list = util.check_get_real_ns()  # NS name changed to /dev/nvme0n2 after some PERST, the same as on SS drive, no idea Y
                util.execute_cmd("sudo nvme format {} -l {} -f".format(ns_list[0], lbaf))
                index += 1

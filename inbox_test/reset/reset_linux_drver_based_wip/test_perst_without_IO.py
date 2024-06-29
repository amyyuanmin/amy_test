# -*- coding: utf-8 -*-

import time, os
import random
import pytest
import logging
import quarchpy
from quarchpy.device import *
from common import util

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
    glitch_mapping = {"100ms": "500us 200", "100us": "500ns 200"}
    logging.info("Wait {}s and issue PERST".format(delay))
    time.sleep(delay)
    logging.info("PERST by Quarch with {} glitch".format(glitch))
    device.sendCommand("SIGnal:PERST:GLITch:ENAble ON")
    device.sendCommand("GLITch:SETup {}".format(glitch_mapping[glitch]))  
    device.sendCommand("SIGnal:PERST:DRIve:OPEn LOW")
    device.sendCommand("RUN:GLITch ONCE")

def test_perst_without_io(device, loop):   
    logging.info("Prefill the drive")
    pci_addr_list = util.get_pci_addr_list()
    util.remove_device(pci_addr_list[0])
    util.rescan_device()
    util.fio_runner()
    
    for i in range(0, int(loop)):
        logging.info("###Loop: {}###".format(i))
        flag = random.randint(0, 1000)
        logging.info('flag: {}'.format(flag))
        if flag % 2 == 0:
            glitch = "100ms"
        else:
            glitch = "100us"
            
        quarch_perst(10, device, glitch)
        util.remove_device(pci_addr_list[0])
        util.rescan_device()

    
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
import sys
import re
from sfvs.nvme import nvme
import sfvs.nvme_io
from sfvs.nvme.utils import Utils as utils
import filecmp
import time
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')
class SMART():
    def __init__(self, LOGGER):
        #Find First NVme device in host
        host = nvme.Host.enumerate()[0]
        #host=hosts[0]
        self.ctrl = host.controller.enumerate()[0]
        self.ns = self.ctrl.enumerate_namespace()[0]
        #Find first namespace device of first NVMe device  
    
        #self.LOGGER = LOGGER
        
    def all_smart_data(self , keyword):
        """
        Get all smart data
        :return: all smart data
        """
        all_smart_data = None
        try:
            with self.ctrl:
                all_smart_data = self.ctrl.smart_log()
                #print(all_smart_data )
                if keyword == 'data_units_read':
                    smart_data = all_smart_data.data_units_read        
                if keyword == 'data_units_written':
                    smart_data = all_smart_data.data_units_written
                if keyword == 'power_on_hours':
                    smart_data = all_smart_data.power_on_hours
                if keyword == 'power_cycles':
                    smart_data = all_smart_data.power_cycles
                if keyword == 'host_read_commands':
                    smart_data = all_smart_data.host_reads   
                if keyword == 'host_write_commands':
                    smart_data = all_smart_data.host_writes
                if keyword == 'available_spare':
                    smart_data = all_smart_data.avail_spare
                if keyword == 'available_spare_threshold':
                    smart_data = all_smart_data.spare_thresh
                if keyword == 'percentage_used':
                    smart_data = all_smart_data.percent_used  
                if keyword == 'unsafe_shutdowns':
                    smart_data = all_smart_data.unsafe_shutdowns
                if keyword == 'critical_warning':
                    smart_data = all_smart_data.critical_warning
                if keyword == 'temperature':
                    smart_data = all_smart_data.temperature
                if keyword == 'media_errors':
                    smart_data = all_smart_data.media_errors
                if keyword == 'num_err_log_entries':
                    smart_data = all_smart_data.num_err_log_entries
                if keyword == 'warning_temp_time':
                    smart_data = all_smart_data.warning_temp_time
                if keyword == 'critical_comp_time':
                    smart_data = all_smart_data.critical_comp_time
                if keyword == 'thm_temp1_trans_count':
                    smart_data = all_smart_data.thm_temp1_trans_count
                if keyword == 'thm_temp2_trans_count':
                    smart_data = all_smart_data.thm_temp2_trans_count
                if keyword == 'thm_temp1_total_time':
                    smart_data = all_smart_data.thm_temp1_total_time
                if keyword == 'thm_temp2_total_time':
                    smart_data = all_smart_data.thm_temp2_total_time
         
                #print ('smart_{} value is: {}'.format(keyword,smart_data))
        except nvme.NVMeException as e:
            logging.info('Error: {}'.format(str(e)))
            sys.exit()
        return smart_data
    
        
    def check_smart_data(self, keyword, original_value, increasement):
        """
        Check the data of specified item(keyword) after IO, if as expected
        :return: Pass or fail
        """        
        time.sleep(5) #sleep some seconds to let smart refresh
        value_after = self.all_smart_data(keyword)    
        logging.info('value_after is {}'.format(value_after))
        result = ''
        
        expect = original_value + increasement
        real = int(value_after)-original_value
        logging.info('expect is {}'.format(expect))
        #print(original_value)
        #print(increasement)
        logging.info('The real increasement is: '+str(real))
        
        logging.info('The real smart data of {} after test is: {}, real increasement is: {}'.format(keyword, value_after, real))
        #define some acceptable gap
        if expect - 1 < int(value_after) < expect + 1:
            result = 'Pass'    
        else:
            result = 'Fail'        
        # print('Check smart data of - '+keyword+" : "+result)    
        logging.info('Check smart data of - '+keyword+" : "+result) 
        return result
    
    #def read_write_io(self, sbl, num_block, pattern='random', write_file='write_random.bin', read_file='read_random.bin'):
    def read_write_io(self, size):
        """
        Do some read write operation
        :size: expect IO data size in GiB
        :return: SMART value expected increasement 
        """    
        logging.info('Do read/write via FVT tool with size of {} GiB'.format(size))
        #256 blocks at one time,num_block This is a 0's based value. 255 means 128k 
        sbl = 0
        num_block = 255
        
        #the patter for IO is set to random, two files used to verify that what read is what write
        write_file = 'write_random.bin'
        read_file = 'read_random.bin'
        pattern = 'random'
        
        #how many times to write the $size GiB data to device
        loop_times = int(int(size)*1024*1024/128)
        logging.info('loop_times:{}'.format(loop_times))
        
        self.ns.open()
        ret = 0
        for i in range(0, loop_times):
            if i%1000 == 0: 
                logging.info('IO loop: ' + str(i))
            #create data file
            seed, data_write = utils.create_dat_file(pattern, data_size=512, file_name=write_file)
        
            #write
            ret, latency = self.ns.write(slba = sbl, nlb = num_block, data = data_write)
            #assert ret == 0, 'Write failed'
            if ret != 0:
                # print('Write failed')
                logging.error('Write failed')
                return -1, 0 , 0
        
            #read
            ret, latency, dat, mdat = self.ns.read(slba = sbl, nlb = num_block, data_size = 512, data_file = read_file)
            #assert ret == 0, 'Read failed'
            if ret != 0:
                # print('Read failed')
                logging.error('Read failed')       
                return -1, 0 , 0
        
            #compare the result
            ret = filecmp.cmp(write_file, read_file)
            #assert ret == True, 'Read data are not what write'
            if ret != True:
                # print('Read data are not what write')
                logging.error('Read data are not what write')   
                return -1, 0 , 0
        
        #Do calculation of SMART value increasement, the data_size is 512, so the calculation is as below
        host_commands_increasement = loop_times
        data_units_increasement = host_commands_increasement* (num_block+1)*512/1000/512
        # print('The expected increasement of data units is: '+str(int(data_units_increasement)))
        logging.info('The expected increasement of data units is: {}'.format(int(data_units_increasement)))
        logging.info('The expected increasement of host commands is: {}'.format(int(host_commands_increasement)))
        # print('The expected increasement of host commands is: '+str(int(host_commands_increasement)))
        
        return ret, host_commands_increasement, data_units_increasement
    
    def run_smart_data(self, keyword, size):
        """
        main portal for all smart data checking methods, due to keyword
        """
        logging.info('Start testing for SMART item: {}'.format(keyword))
        logging.info('Start testing for SMART item: {}'.format(keyword))
        if keyword in ['data_units_read', 'data_units_written', 'host_read_commands', 'host_write_commands']:
            result = self.run_smart_data_read_write(keyword,size)
        if keyword in ['available_spare', 'available_spare_threshold', 'percentage_used']:
            result = self.run_smart_data_available_spare(keyword)
        
        return result
        
    def run_smart_feature(self, keyword): 
        # print('Start testing for SMART item: {}'.format(keyword))
        logging.info('Start testing for SMART item: {}'.format(keyword))
        self.run_smart_power(keyword)
        return 'Pass'
        
    def run_smart_data_read_write(self, keyword,size):
        """
        Test SMART for IO related: data_units_read/data_units_written/host_read_commands/host_write_commands
        """
        #get smart value before io
        value_before = self.all_smart_data(keyword)
        logging.info('The value of {} before testing is: {}'.format(keyword, value_before))
    
        logging.info('read/write size is {} GB'.format(size))
        logging.info('read/write size is {} GB'.format(size))
        #do some IO
        ret, host_commands_increasement, data_units_increasement = self.read_write_io(size)
        if ret == -1:
            return 'Fail'
        #check the increasement of smart value
        if keyword == 'host_read_commands' or keyword == 'host_write_commands':
            result = self.check_smart_data(keyword, int(value_before), host_commands_increasement)
            logging.info('result is {}'.format(result))
            # print('result is {}'.format(result))
        elif keyword == 'data_units_written' or keyword == 'data_units_read':
            result = self.check_smart_data(keyword, int(value_before), data_units_increasement)
            logging.info('result is {}'.format(result))
            # print('result is {}'.format(result))
        
        return result
        
    def run_smart_power(self, keyword):
        """
        Test SMART for: power_cycles, power_on_hours
        """
        value_before = self.all_smart_data(keyword)
        # print('{} value: {}'.format(keyword, value_before))
        logging.info('{} value: {}'.format(keyword, value_before))
        if keyword == 'power_on_hours':
            if value_before > 1: #this test executed within 1 hour after flash
                return 'Fail'
            else:
                return 'Pass'
        #value_after = self.all_smart_data(keyword)
        
        return 'Pass'

    def run_smart_power_cycles(self, keyword):
        """
        Test SMART for: power_cycles
        """
        value_before = self.all_smart_data(keyword)
        logging.info('{} value: {}'.format(keyword, value_before))

        value_after = self.all_smart_data(keyword)
        if keyword == 'power_cycles':
            if value_after - value_before > 0: #this test executed within 1 hour after flash
                return 'Pass'
            else:
                return 'Fail'
        #value_after = self.all_smart_data(keyword)
        
        return 'Pass'

    def run_temperature(self, keyword):
        '''
        Test SMART for: temperature
        '''
        value = self.all_smart_data(keyword)
        # print('{} value: {}'.format(keyword, value))
        logging.info('{} value: {}'.format(keyword, value))        
        if value > 65:
            return 'Fail'
        else:
            return 'Pass'
    
    def run_smart_data_available_spare(self, keyword):
        """
        Test SMART for: available_spare/available_spare_threshold/percentage_used
        """
        value_before = self.all_smart_data(keyword)
        # print('{} value: {}'.format(keyword, value_before))
        logging.info('{} value: {}'.format(keyword, value_before))
        value_after = self.all_smart_data(keyword)
        logging.info('{} value: {}'.format(keyword, value_after))
        return 'Pass'       
    
if __name__ == "__main__":
    LOGGER = None
    test = SMART(LOGGER)
    test.run_smart_data_read_write('data_units_written')
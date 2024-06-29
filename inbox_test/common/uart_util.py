#!/usr/bin/python
######################################################################################################################
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
#  $Id$
#  revision: 0.1
#
#  Author:  Leon Cheng
#
#  Feb. 17, 2022
#
#####################################################################################################################

import logging
import os, time
from datetime import datetime, timedelta
import rpyc
from . import util
import pytest
import re

class UART_Util:
    def __init__(self, rpi_ip, rpi_path, fw_log_indicator = "fw_log.log"):
        self.rpi_path = rpi_path
        self.rpi_ip = rpi_ip
        self.fw_log_indicator = fw_log_indicator + "."
        self.fw_log = []  # in case the new fw log just created, we need to check both logs
        self.offset = self.get_end_offset()
        
    def send_uart_cmd(self, uart_cmd, end_keyword = None, wait_time = 3, timeout = 10, return_log = False):
        '''
        Send UART cmd to fw
        end_keyword: if None, skip check UART execution result
        '''
        try:
            conn = rpyc.connect(self.rpi_ip, 18812)
            logging.info("UART cmd is: {}".format(uart_cmd))
            conn.root.echo(uart_cmd)
            if end_keyword == None:
                logging.warning("No UART result check")
            else:
                ret = self.check_uart_result(uart_cmd, end_keyword, wait_time = wait_time, timeout = timeout, return_log = return_log)
                if not return_log and not ret:
                    pytest.fail("UART cmd executed failed")
                elif return_log:
                    if not ret[0]:
                        pytest.fail("UART cmd executed failed")
                    else:
                        return ret[1]  # return logs
        except Exception as e:
            logging.error("Error occurred during send uart cmd: {}".format(e))
            pytest.fail("Error occurred during send uart cmd: {}".format(e))
        finally:
            conn.close()
        
    def check_uart_result(self, uart_cmd, end_keywords, wait_time, timeout, return_log = False):
        '''
        Check if the UART cmd excuted completed
        Add handler if one new fw log just created
        uart_cmd: the searching start point
        end_keywords: keyword(or reg expression) to indicate that UART cmd executed successfully, you can also specify a keyword list and all keywords will be matched
        wait_time: wait time before check next time
        timeout: timeout for the UART cmd
        return_log: if capture specified log after uart cmd executed
        '''
        wait_until = datetime.now() + timedelta(minutes=int(timeout))
            
        flag = 0 # indicate the search result on the first fw log, 0 - neither found, 1 - found start
        if type(end_keywords) != list:
            end_keywords = [end_keywords]

        if return_log:
            logs = []
        while True:
            self.sync_fw_log()
            # If two fw log need to be checked at the same time, this only happens once at a time. 
            # For ex, if in while loop 1, two fw log exists and not all search succeeed, 
            # then at while loop 2, only the latest fw log exsits,
            # the old fw log removed during sync_fw_log
            filename = self.fw_log[0]
            if len(self.fw_log) == 2:
                filename_tmp = self.fw_log[1]
                
            # logging.info("Last offset: {}".format(self.offset))
            with open(filename, "r") as log:
                log.seek(self.offset)
                if flag != 1:
                    logging.debug("Start finding the start point on {}....".format(filename))
                    while True:
                        line = log.readline()
                        if uart_cmd in line:
                            logging.debug("Start line:{}".format(line))
                            pos = log.tell()
                            logging.debug("Start offset: {}".format(pos))
                            flag = 1
                            break                    
                    log.seek(pos)
                    self.offset = pos

                lines = log.readlines()
                for line in lines:
                    for end_keyword in end_keywords:
                        if end_keyword in line or re.search(end_keyword, line) != None:
                            logging.debug("Found matched line: {}".format(line))
                            if return_log:
                                logs.append(line)
                            self.offset = log.tell()  # update offset
                            end_keywords.remove(end_keyword)
                            if end_keywords == []:  # found all keywords
                                logging.info("Execute completed")
                                if len(self.fw_log) == 2:
                                    self.offset = 0
                                if return_log:
                                    return True, logs
                                else:
                                    return True
            
            # if new fw log file created
            if len(self.fw_log) == 2:
                with open(filename_tmp, 'r') as log:
                    if flag == 1:  # Start point found on first fw log
                        lines = log.readlines()
                        for line in lines:
                            for end_keyword in end_keywords:
                                if end_keyword in line or re.match(end_keyword, line) != None:
                                    logging.debug("Found matched line: {}".format(line))
                                    if return_log:
                                        logs.append(line)
                                    self.offset = log.tell()  # update offset
                                    end_keywords.remove()
                                    if end_keywords == []:
                                        logging.info("Execute completed")
                                        if return_log:
                                            return True, logs
                                        else:
                                            return True
                    elif flag == 0:  # No match found on first fw log
                        while True:
                            logging.debug("Start finding the start point on {}....".format(filename_tmp))
                            line = log.readline()
                            if uart_cmd in line:
                                logging.debug("Start line:{}".format(line))
                                pos = log.tell()
                                logging.debug("Start offset: {}".format(pos))
                                break
                            log.seek(pos)

                            lines = log.readlines()
                            for line in lines:
                                for end_keyword in end_keywords:
                                    if end_keyword in line or re.match(end_keyword, line) != None:
                                        logging.debug("Found matched line: {}".format(line))
                                        if return_log:
                                            logs.append(line)
                                        self.offset = log.tell()  # update offset
                                        end_keywords.remove()
                                        if end_keywords == []:
                                            logging.info("Execute completed")
                                            if return_log:
                                                return True, logs
                                            else:
                                                return True
            
            if wait_until < datetime.now():
                logging.info("Execute timeout")
                return False		
            time.sleep(wait_time)

    def sync_fw_log(self):
        '''
        Sync fw log increasingly from RPI to host for UART check
        '''
        self.get_latest_fw_log()
        for fw_log in self.fw_log:
            sync_cmd = "rsync -t -e 'ssh -o StrictHostKeyChecking=no -p 22' pi@{}:/{} ./".format(self.rpi_ip, os.path.join(self.rpi_path.strip("/lib/util"), fw_log))
            util.ssh_cmd(sync_cmd, self.rpi_ip, eliminate_log=True)

    def get_latest_fw_log(self):
        '''
        Get the latest fw log file, in case there're severl fw logs available
        '''
        check_cmd = "ls {}* | wc -l".format(os.path.join(self.rpi_path, self.fw_log_indicator))
        ret, out = util.ssh_cmd(check_cmd, self.rpi_ip, out_flag = True, eliminate_log=True)
        fw_log_tmp = self.fw_log_indicator + str(int(out) - 1) 
        # to simplify the method, we assume there're at most 2 fw log at the same time
        # Actually there should be at most 2, it's not possible that fw log increased more than 100m at one UART cmd
        if (fw_log_tmp not in self.fw_log):  
            self.fw_log.append(fw_log_tmp)
        elif fw_log_tmp in self.fw_log and len(self.fw_log) == 2:
            self.fw_log.remove(self.fw_log[0])
        
    def get_end_offset(self):
        '''
        Initialize the offset. 
        If there're already keyword exists in fw log, might get the former location rather than the latest one, so update the offset to the end of fw log before send uart cmd
        '''
        try:
            self.sync_fw_log()
            with open(self.fw_log[0], "r") as f:
                offset = f.seek(0, 2)  #search from the end
        except Exception as e:
            logging.error("Exception: {}".format(e))
            offset = 0
        logging.debug("Initial offset: {}".format(offset))
        return offset
    
    def uart_format(self):
        '''
        Send UART Format cmd and check response
        '''
        self.offset = self.get_end_offset()
        logging.debug('Issue UART Format')
        keywords = ["\[C0C0\]Ftl Erase: .* supper block excute successfully,", 
                            "\[C0C1\]Ftl Erase: .* supper block excute successfully,", 
                            "\[C0C2\]Ftl Erase: .* supper block excute successfully,",
                            "\[C0C3\]Ftl Erase: .* supper block excute successfully,"]
        self.send_uart_cmd("FORMAT", keywords, wait_time=3)
    
    def alloc_buffer(self, size):
        '''
        UART cmd to allocate memory
        size: memory size in bytes to be allocated, it's a HEX value
        return: a str of HEX value
        [2022-05-13 10:53:12.052] ALLOC 1 1018
        [2022-05-13 10:53:12.060] [C0C0]2B401094
        [2022-05-13 10:53:12.069] [C0C0]M
        '''
        logging.info("Allocate memory for 0x{} bytes".format(size))
        buffer_addr = None
        logs = self.send_uart_cmd("ALLOC 1 {}".format(size), ["C0C0", "C0C0"], return_log = True)
        for log in logs:
            temp = log.split("[C0C0]")[1].strip()
            if len(temp) > 4:  # refer to output example above
                buffer_addr = temp 
                break
        else:
            logging.error("No buffer address detected") 
            pytest.fail("No buffer address detected")            
        logging.info("Allocated buffer at address: {}".format(buffer_addr))
        return buffer_addr
    
    def mem_copy(self, src_addr, dst_addr, size):
        '''
        Memory copy from src to dst
        size: size in bytes, it's a hex value
        '''
        logging.info('Memory copy from {} to {}'.format(src_addr, dst_addr))
        self.send_uart_cmd("MEMCPY {} {} {}".format(dst_addr, src_addr, size)) # dest comes before src in the UART, no keyword to indicate the success
        
    def mem_set(self, buffer_addr, pattern, size):
        '''
        Set data to the buffer
        pattern: data to be filled
        size: data size in byte, it's a hex value
        '''
        logging.info('Fill buffer {} with pattern {} for 0x{} bytes'.format(buffer_addr, pattern, size))
        self.send_uart_cmd("MEMSET {} {} {}".format(buffer_addr, pattern, size)) # no keyword to indicate the success
        
    def xorfill(self, buffer_addr, pattern, size, crc_enalbe = 0, hlba_enable = 0, mpecc_enable = 0, hlba = 0):
        '''
        Perform XOR pattern fill
        pattern: data to be filled
        size: data size in byte, it's a hex value
        '''
        logging.info("XOR fill buffer {} with pattern {} for 0x{}bytes".format(buffer_addr, pattern, size))
        self.send_uart_cmd("XORFILL {} {} {} {} {} {} {}".format(buffer_addr, pattern, size, crc_enalbe, hlba_enable, mpecc_enable, hlba), "Command success")
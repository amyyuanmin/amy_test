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
#  May. 12, 2022
#
#####################################################################################################################

import logging
import sys
sys.path.append("../")
from common.uart_util import UART_Util

class Dmac_Util():
    def __init__(self, rpi_ip, rpi_path, fw_log_indicator):
        self.uart_util = UART_Util(rpi_ip, rpi_path, fw_log_indicator)
            
    def enc_fill(self, mode, buffer_addr, pattern, size, hlba, crc_enable = 1, hlba_enable = 1, mpecc_enable = 1, nsid = 1):
        '''
        Fill the buffer with encrypted data 
        mode: block fill or queue fill
        buffer_addr: buffer address allocated
        pattern: plain data to be filled
        size: size of bytes in hex
        hlba: HLBA
        Others are default in uart, thus not accept params
        '''
        if mode == "block":
            uart_cmd = "XORENCBLOCKFILL"
        elif mode == "queue":
            uart_cmd = "XORENCQUEUEFILL"
        logging.info("Encryption fill in {} mode, buffer {} with pattern {} for 0x{} bytes.".format(mode, buffer_addr, pattern, size))
        full_cmd = "{} {} {} {} {} {} {} {} {}".format(uart_cmd, buffer_addr, pattern, size, crc_enable, hlba_enable, mpecc_enable, hlba, nsid)
        
        self.uart_util.send_uart_cmd(full_cmd, "Command success")
        
    def t10_enc_fill(self, mode, buffer_addr, pattern, size, hlba, lbaf, crc_enable = 1, hlba_enable = 1, mpecc_enable = 1, nsid = 1, pil = 0, apptag = None, reftag_msb = 0, reftag_lsb = None, enc_enable = 1, guard_size_sel = 0, guard_swap = 0, storagetag_msb = 0, storagetag_lsb = 0, storagetag_size = 0, soc_ver = 0):
        '''
        Fill the buffer with encrypted data with E2E data protection
        test under which lbaf, basically determine the meta size
        mode: block fill or queue fill
        buffer_addr: buffer address allocated
        pattern: plain data to be filled
        size: size of bytes in hex
        hlba: HLBA
        PIL: 0----last 8 bytes of metadata
            1----first 8 bytes of metadata
        reftag_lsb: hlba
        Others are default in uart, thus not accept params
        This based on Ax board, if B0 enabled, value of some params need to be updated
        '''
        meta_size_map = {"8": 10, "13": 8}
        if mode == "block":
            uart_cmd = "XORT10ENCBLOCKFILL"
        elif mode == "queue":
            uart_cmd = "XORT10ENCQUEUEFILL"
        logging.info("Encryption fill in {} mode with E2E protection, buffer {} with pattern {} for 0x{} bytes.".format(mode, buffer_addr, pattern, size))
        full_cmd = "{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} {11} {12} {13} {14} {15} {16} {17} {18} {19} {20}".format(uart_cmd, buffer_addr, pattern, size, crc_enable, hlba_enable, mpecc_enable, hlba, nsid, meta_size_map[lbaf], pil, guard_size_sel, guard_swap, apptag, storagetag_msb, storagetag_lsb, storagetag_size, reftag_msb, reftag_lsb, enc_enable, soc_ver)
        
        self.uart_util.send_uart_cmd(full_cmd, "Command success")
        
    def enc_copy(self, mode, src_addr, dst_addr, size, hlba, crc_enable = 1, hlba_enable = 1, mpecc_enable = 1, nsid = 1):
        '''
        Copy the data from SRC to DEST with encryption
        mode: copy in block or queue mode
        src_addr: src buffer address allocated
        dst_addr: dst buffer address allocated
        size: size of bytes in hex
        hlba: HLBA
        Others are default in uart, thus not accept params
        '''
        if mode == "block":
            uart_cmd = "XORENCBLOCKCPY"
        elif mode == "queue":
            uart_cmd = "XORENCQUEUECPY"
            
        full_cmd = "{} {} {} {} {} {} {} {} {}".format(uart_cmd, src_addr, dst_addr, size, crc_enable, hlba_enable, mpecc_enable, hlba, nsid)
        self.uart_util.send_uart_cmd(full_cmd, "Command success")

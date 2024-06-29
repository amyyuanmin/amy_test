#!/usr/bin/python
######################################################################################################################
# Copyright (c) 2021 Marvell Semiconductor.  All Rights Reserved.
#
# The contents of this software are proprietary and confidential to Marvell Technology. and are limited in distribution
# to those with a direct need to know. Individuals having access to this software are responsible for maintaining the
# confidentiality of the content and for keeping the software secure when not in use. Transfer to any party is strictly
# forbidden other than as expressly permitted in writing by Marvell Technology.
#
# Copyright (c) 2021 Marvell Semiconductor.
#
# Version Control Information:
#
#  $Id$
#  revision: 0.3
#
#  Author:  Leon Cheng
#
#  May. 25, 2021
#
#####################################################################################################################
import os
import logging
import pytest

logging.basicConfig(level=logging.INFO,format='[%(asctime)s.%(msecs)03d] %(levelname)s %(filename)s(line:%(lineno)d): %(message)s')

class Data_Analyzer:
    def __init__(self, data_file, perf_output, case_name, type = None):
        '''
        data_file: fio result file, it's file path
        perf_output: file to record perf data
        type: specify the result type required: IOPS or BW
        '''
        if os.path.exists(data_file):
            self.data_file = data_file
        else:
            logging.error("No fio result file found")
            pytest.fail("No fio result file found")
        
        if type != None:
            if type.upper() == 'BW':
                self.type = 'bw' # in fio result file, bw is in lower case: READ: bw=54.0MiB/s (56.6MB/s), 54.0MiB/s-54.0MiB/s (56.6MB/s-56.6MB/s), io=3241MiB (3398MB), run=60001-60001msec
                self.unit = 'MB/s'
            elif type.upper() == 'IOPS':
                self.type = 'IOPS' # in fio result file, IOPS is in lower case: read: IOPS=13.8k, BW=54.0MiB/s (56.6MB/s)(3241MiB/60001msec)
                self.unit = 'KIOPS'
        else: # by default, get BW for sequential test while IOPS for random test
            if 'seq' in data_file:
                self.type = 'bw'
                self.unit = 'MB/s'
            elif "rand" in data_file:
                self.type = 'IOPS'
                self.unit = 'KIOPS'

        self.perf_output = perf_output
        if not os.path.exists(self.perf_output):
            with open(self.perf_output, 'w') as f:
                f.write("[performance]\n")  # add a head for configparser usage
                logging.info("Create perf result file: {}".format(self.perf_output))

        # not hard code in scripts for test items, determine via test name
        # self.mapping = {
        #     "seqwr_128k_iodepth_512": "seq_write(MB/s)",
        #     "seqrd_128k_iodepth_512": "seq_read(MB/s)",
        #     "randwr_4k": "random_write(KIOPS)",
        #     "randrd_4k_iodepth_8x64": "randrd_4k_iodepth_8x64(KIOPS)",
        #     "seqwr_128k_iodepth_1x16": "seq_write_128k_iodepth_1x16(MB/s)",
        #     "seqrd_128k_iodepth_1x16": "seq_read_128k_iodepth_1x16(MB/s)",
        #     "seqwr_128k_iodepth_4x32": "seq_write_128k_iodepth_4x32(MB/s)",
        #     "seqrd_128k_iodepth_4x32": "seq_read_128k_iodepth_4x32(MB/s)",
        #     "seqrd_128k_iodepth_1x128": "seq_read_128k_iodepth_1x128(MB/s)",
        #     "seqwr_128k_iodepth_1x128": "seq_write_128k_iodepth_1x128(MB/s)",        
        # }

        self.perf_item = "{}({})".format(case_name, self.unit)
        # for key, value in self.mapping.items():
        #     if key in data_file:
        #         self.perf_item = value
        #         break
        # else:
        #     logging.error("No matched perf item found")
        #     pytest.fail("No required info found")

    def get_perf_data(self):
        '''
        Get perf data from fio result file, BW for seqential test and IOPS for random test
        '''
        result_line = None
        with open(self.data_file, 'r') as file:
            while True:
                out = file.readline()
                if not out:
                    break
                else:
                    if self.type + "=" in out:
                        result_line = out.strip()
                        logging.info("Found result line: {}".format(result_line))
                        break

        if result_line == None:
            logging.error("No required info found")
            pytest.fail("No required info found")

        result_tmp = result_line.split(',')
        result_ele = None
        result = None
        for result_ele in result_tmp:
            if self.type in result_ele:
                result_ele = result_ele.strip()
                logging.info("Matched result info: {}".format(result_ele))
                break
        else:
            logging.error("No mathed result info found")
            pytest.fail("No mathed result info found")
        
        if self.type.upper() == 'IOPS':
            result = result_ele.split('=')[1]
            if result.endswith("k"):
                result = result.strip("k")
            else:
                result = int(result) / 1000
        elif self.type.upper() == 'BW':
            result = result_ele.split('(')[1].strip(")")
            if "MB/s" in result_ele:
                result = result.strip("MB/s")
            elif "GB/s" in result_ele:
                result = float(result.strip("GB/s")) * 1024
            elif "KB/s" in result_ele:
                result = float(result.strip("KB/s")) / 1024
            elif "TB/s" in result_ele:
                result = float(result.strip("TB/s")) * 1024 * 1024
        
        logging.info("Performance result({}): {}".format(self.unit, result))

        try:
            # item = self.data_file.split("/")[-1].strip('fio_').strip('.log')
            with open(self.perf_output, 'a+') as f:
                f.write("{}:{}\n".format(self.perf_item, result))
        except Exception as e:
            logging.error("Write perf data failed: {}".format(e))
            pytest.fail("Write perf data failed: {}".format(e))
        

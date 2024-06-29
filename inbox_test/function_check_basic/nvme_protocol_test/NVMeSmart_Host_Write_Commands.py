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

import logging
from sfvs.nvme import nvme
from sfvs.nvme.utils import Utils as utils
from nvme_protocol_test.fvt_adm_cmd_common import fvt_adm
from nvme_protocol_test.fvt_io_cmd_common import fvt_io
from nvme_protocol_test.smart_lib import SMART

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s : %(message)s')
def verify_host_write_commands(ns_data, ctrl, ns, result_file, loop):
    results_dict = {}
    finalResult = []
    test_io = fvt_io(ctrl, ns)
    smart = SMART(ctrl, ns)
    host = nvme.Host.enumerate()[0]
    ctrl = host.controller.enumerate()[0]
    #step1: Check LBADS value supported for namespace.
    try:
        LBA=find_lba_value(ns_data)
        if LBA!=0:
            logging.info("LBA value found and value is: {}".format(LBA))
            results_dict["LBA_value_found"] = "Passed"
            finalResult.append(0)
        else:
            logging.error("LBA value is not correct")
            results_dict["LBA_value_found"] = "Failed"
            finalResult.append(1)
         #step2: Generating  data size of lbads,2 labds,4 labds
        data_size = generate_data(LBA)
        logging.info('Generated data size list is: {}'.format(data_size))
        #step3: Interating  over data size list 1 by 1
        before_test_data=int(smart.all_smart_data("host_writes"))
        total_increment=0
        for index in data_size:
            increment_value=loop
            total_increment+=increment_value
            current_value=int(smart.all_smart_data("host_writes"))
            logging.info("Current Data Unit Write Value Before Write Operation : {} ".format(current_value))
            write_file = 'write' + str(index) + '.bin'
            logging.info("Creating  file with data size: {}".format(index))
            seed, data_write = utils.create_dat_file(data_size=index, file_name=write_file, seed=index)
            #step4: Iterating complete 1000 loop for every lbads
            flag=True
            for rot in range(loop):
                nlb=index//LBA-1
                slba=rot*index//LBA
                w_ret = test_io.nvme_write_test(slba,nlb,data_write)
                if w_ret!=0:
                    flag=False
            if flag==False:
                logging.info("Write Command Failed")
                finalResult.append(1)
            else:
                logging.info("Write Command {} executed successfully for LBADS {}".format(rot, index))
                finalResult.append(0)
            After_Write_Value=int(smart.all_smart_data("host_writes"))
            logging.info("Current Data Unit Write Value After Write Operation : {} ".format(After_Write_Value))
            result=smart.validate_smart_data(current_value,After_Write_Value,increment_value)
            if result==True:
                logging.info("This test passed for LBADS {}".format(index))
                logging.info("Current data unit written  value: {}".format(current_value))
                logging.info("After Write data unit value: {}".format(After_Write_Value))
                results_dict["data_unit_write_test_with_lbads_{}".format(str(index))]="Passed"
                finalResult.append(0)
            else:
                logging.info("This test failed for LBADS {}".format(index))
                logging.info("Current data unit written  value: {}".format(current_value))
                logging.info("After Write data unit value: {}".format(After_Write_Value))
                results_dict["data_unit_write_test_with_lbads_{}".format(str(index))] = "Failed"
                finalResult.append(1)
        result=smart.validate_smart_data(before_test_data,After_Write_Value,total_increment)
        if result==True:
            logging.info("This test passed after complete write operation of data")
            results_dict["Result_after_complete_write_operation_of_data_size"]="Passed"
            finalResult.append(0)
        else:
            logging.info("This test failed after complete write operation of data")
            results_dict["Result_after_complete_write_operation_of_data_size"] = "Failed"
            finalResult.append(1)
    except Exception as e:
        logging.error("Not working with Error: {}".format(str(e)))
        finalResult.append(1)
    with open("{}/Host_Write_Commands.log".format(result_file), 'w+') as f:
        for count, (k, v) in enumerate(results_dict.items()):
            count += 1
            logging.info("Step {}. {} : {}".format(count, k, v))
            f.write("Step {}. {} : {}\n".format(count, k, v))
        logging.info('\n')
        if 1 in finalResult:
            logging.error("TC-3  SMART_LOG: Host Write Commands : Failed")
            f.write("\nTC-3  SMART_LOG: Host Write Commands: FAILED\n")
            logging.error("test_case Failed")
            result = "FAILED"
            #return -1
        else:
            logging.info("TC-3  SMART_LOG: Host Write Commands : PASSED")
            f.write("\nTC-3  SMART_LOG: Host Write Commands: PASSED\n")
            logging.info("test_case passed")
            result = "PASSED"
        f.close()
        return result
#this function for finding LBA value
def find_lba_value(ns_data):
    try:
            data_s = str(ns_data)
            for i in data_s.split():
                if i.startswith("lbads"):
                    lbaf = i
            data = lbaf.split(":")
            return pow(2, int(data[1]))
    except Exception as e:
        logging.error("Unable to find LBAF option in data Structure: {}".format(e))
# this function to  generate data based on LBADS
def generate_data(LBA):
    data_size=[]
    for index in range(3):
        data_size.append(pow(2, index) * LBA)
    return data_size

def main(ctrl, ns, result_file):
    test = fvt_adm(ctrl, ns)
    ns_data = test.ns_identify()
    logging.info("\n ")
    logging.info("###############################################################")
    logging.info("#              TC-3  SMART_LOG: Host Write Commands           #")
    logging.info("###############################################################")
    loop=1000
    logging.info("No. of iteration to  perform write  operation: {}".format(loop))
    return verify_host_write_commands(ns_data, ctrl, ns, result_file, loop)
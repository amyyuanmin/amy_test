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
#  revision: 0.1
#
#  Author:  Leon Cheng
#
#  May. 12, 2021
#
#####################################################################################################################

import pytest
import logging
import time, os, shutil
from itertools import product
import random
import sys
sys.path.append("../")
from common import fvt_adm_cmd_common
from log_config import MyLog
#import logger

class Test_Format:
    @pytest.fixture(scope='class', autouse=True)
    def setup_teardown(self, controller, namespace, hostname):
        global adm_common, logger, test_flag
        logger = MyLog("runtime_console.log")
        test_flag = 0
        adm_common = fvt_adm_cmd_common.fvt_adm(controller, namespace)

    @pytest.fixture(scope='function', autouse=True)
    def result_handler(self, request):
        global test_flag
        if test_flag != 0:
            logger.error("CI test and former test failed, abort test")
            pytest.exit("Former test failed, abort test")

    def get_format_feature(self, format_lbaf):
        size_list0 = [0, 9, 10, 11, 12, 13, 14, 15, 16]
        size_list1 = [1, 2, 3, 4, 5, 6, 7, 8]
        meta_8_list = [5, 6, 12, 13]
        meta_16_list = [7, 8, 14, 15]
        lba_size_refer = 0
        metadata = 0
        if format_lbaf in meta_8_list:
            metadata = 8
        if format_lbaf in meta_16_list:
            metadata = 16

        if format_lbaf in size_list0:  # 512 byte LBA
            lba_size_refer = 512
        elif format_lbaf in size_list1:
            lba_size_refer = 4096
        return lba_size_refer, metadata
        
    def format(self, format_lbaf, pi, pil ):
        global adm_common
        result = "Fail"
        size_list0 = [0, 9, 10, 11, 12, 13, 14, 15, 16]
        size_list1 = [1, 2, 3, 4, 5, 6, 7, 8]
        meta_8_list = [5, 6, 12, 13]
        meta_16_list = [7, 8, 14, 15]
        lba_size_refer = 0
        metadata = 0
        if format_lbaf in meta_8_list:
            metadata = 8
        if format_lbaf in meta_16_list:
            metadata = 16
        try:
            ret = adm_common.e2e_data_protection_format(format_lbaf, pi, pil)
            time.sleep(1)
            if ret == 0:
                ns_data = adm_common.ns_identify()
                if ns_data != -1:
                    flbas = ns_data.flbas
                    lba_ds = ns_data.lbaf(flbas & 0x0F).ds
                    lba_size = 2 ** lba_ds	
                    
                    logging.info("Identify LBA size: {} ,protection info type: {} protection info location: {}".format(lba_size, pi, pil))
                                 
                    if format_lbaf in size_list0:  # 512 byte LBA
                        lba_size_refer = 512
                    elif format_lbaf in size_list1:
                        lba_size_refer = 4096

                    if lba_size == lba_size_refer:
                        logging.info("Format to {} LBA size successfully".format(lba_size))
                        result = "Pass"
                    else:
                        logging.error("Real lba size: {}, expected: {}".format(lba_size, lba_size_refer))
                        result = "Fail"
                    
                    if str(flbas) == str(format_lbaf):
                        logging.info("Format to flbas:{} successfully".format(flbas))
                    else:
                        logging.error("Real flbas: {}, expected: {}".format(flbas, format_lbaf))
                        result = "Fail"
                        
        except Exception as e:
            logging.error("Initialize failed:{}".format(e))
            return result, lba_size_refer, metadata
        
        finally:
            return result, lba_size_refer, metadata

    @pytest.mark.timeout(method="signal")
    def test_E2e_data_protection_error_cases(self):
        global test_flag
        lba_format_list = [5, 6, 12, 7 ,8 ,14]
        tmp = random.randint(0,5)
        lba_format = lba_format_list[tmp]
        nlb, slba = 1, 8
        pil_list = [0, 1]
        tmp = random.randint(0,1)
        pil = pil_list[tmp]
        logging.info("Random choose LBAF:{}, PIL:{} to test error cases".format(lba_format, pil))
        test_flag = -1
        #Create Golden Sample
        pi_list = [1, 2, 3] #type 1,2 
        for pi in pi_list:
            format_result, byte_per_lba, byte_per_metadata = self.format(lba_format, pi, pil)
            if format_result == 'Fail':
                logging.error('Format Failed with lba_format: {}, pi: {}, pil: {}'.format(lba_format, pi, pil))
                pytest.fail()    
                
            #logging.info("===========================START================================")
            write_pattern = random.randint(1,9)
            #logging.info("Write pattern: {}".format(write_pattern))
            write_file = 'write_file.bin'
            write_file_big = 'write_file_big.bin'
            read_data_file = 'read_data.bin'
            metadata_pattern = random.randint(1,9)
            #logging.info("metadata pattern: {}".format(metadata_pattern))
            metadata_file = 'metadata_file.bin'
            read_mdata_file = 'read_mdata.bin'
            apptag = random.randint(1,8)
            reftag = slba
            write_data = adm_common.e2e_data_protection_create_dat_file_by_LBA(write_pattern, nlb, write_file, byte_per_lba)
            write_data_big = adm_common.e2e_data_protection_create_dat_file_by_LBA(write_pattern, nlb*10, write_file_big, byte_per_lba)
            metadata_data = adm_common.e2e_data_protection_create_dat_file_by_LBA(metadata_pattern, nlb, metadata_file, byte_per_metadata)
            data_size = nlb*byte_per_lba
            mdata_size = nlb*byte_per_metadata
            if pi == 3: #type 3 does not check bit 0, if check, it would fail
                prinfo = 14
            else:
                prinfo = 15
            #prinfo = 10 #gordon
            logging.info("Golden Sample paramters:")
            logging.info('write_pattern:{}'.format(write_pattern))
            logging.info('metadata_pattern:{}'.format(metadata_pattern))
            logging.info('apptag:{}'.format(apptag))
            logging.info('reftag:{}'.format(reftag))
            logging.info('nlb:{}'.format(nlb))
            logging.info('slba:{}'.format(slba))
            logging.info('pil:{}'.format(pil))
            logging.info('pi:{}'.format(pi))
            logging.info('lba_format:{}'.format(lba_format))
            logging.info('data_size:{}'.format(data_size))
            logging.info('mdata_size:{}'.format(mdata_size))
            logging.info("=================================")
                        
            write_result = adm_common.e2e_data_protection_nvme_write_test(slba, nlb, write_data, data_size, mdata_size, metadata_data, prinfo, reftag, apptag)
            if write_result != 0:
                logging.error('Golden Sample Write Failed')
                pytest.fail()
                
            #logging.info("Sleep 10 sec")
            time.sleep(10)
            
            #logging.info("Do Read Test")
            read_result, data_read_back, mdata_read_back = adm_common.e2e_data_protection_nvme_read_test(slba, nlb, read_data_file, data_size, mdata_size, read_mdata_file, prinfo-8, reftag, apptag)
            if read_result != 0:
                logging.error('Golden Sample Read Failed')
                pytest.fail() 
            os.system("mv read_mdata.bin metadata_file.bin")
            os.system("mv read_data.bin  write_file.bin")
            logging.info("Now write_file: {} and metadata_file: {} are Golden Sample".format(write_file,metadata_file))
            time.sleep(10)
            with open("metadata_file.bin","rb") as f:
                metadata_data = f.read()
            logging.info("Test Guard field Write Error Handling, Error nlb")
            prinfo = 4
            write_result = adm_common.e2e_data_protection_nvme_write_test(slba, nlb*10, write_data_big, data_size*10, mdata_size, metadata_data, prinfo, reftag, apptag)
            if write_result == 0:
                logging.error("Test Guard field Write Error Handling did not trigger")
                pytest.fail()
            else:
                logging.info("Test Guard field Write Error Handling triggered!!")
            '''
            logging.info("Test Guard field Read Error Handling, Error nlb")
            read_result, data_read_back, mdata_read_back = adm_common.e2e_data_protection_nvme_read_test(slba, nlb, read_data_file, data_size*1000, mdata_size, read_mdata_file, prinfo, reftag, apptag)
            if read_result == 0:
                logging.error("Test Guard field Read Error Handling did not trigger")
                pytest.fail()
            else:
                logging.info("Test Guard field Read Error Handling triggered!!")  
            '''
    
            ##########################################################################
            logging.info("Test Application Tag field Write Error Handling, Error apptag")
            prinfo = 2
            apptag_error = apptag+1
            write_result = adm_common.e2e_data_protection_nvme_write_test(slba, nlb, write_data, data_size, mdata_size, metadata_data, prinfo, reftag, apptag_error)
            if write_result == 0:
                logging.error("Test Application Tag field Write Error Handling did not trigger")
                pytest.fail()
            else:
                logging.info("Test Application Tag field Write Error Handling triggered!!")
            
            logging.info("Test Application Tag field Read Error Handling, Error apptag")
            read_result, data_read_back, mdata_read_back = adm_common.e2e_data_protection_nvme_read_test(slba, nlb, read_data_file, data_size, mdata_size, read_mdata_file, prinfo, reftag, apptag_error)
            if read_result == 0:
                logging.error("Test Application Tag field Read Error Handling did not trigger")
                pytest.fail()
            else:
                logging.info("Test Application Tag field Read Error Handling triggered!!")      
    
            ##########################################################################
            logging.info("Test Reference Tag field Write Error Handling, Error reftag")
            prinfo = 1
            reftag_error = reftag+1
            write_result = adm_common.e2e_data_protection_nvme_write_test(slba, nlb, write_data, data_size, mdata_size, metadata_data, prinfo, reftag_error, apptag)
            if write_result == 0:
                logging.error("Test Reference Tag field Write Error Handling did not trigger")
                pytest.fail()
            else:
                logging.info("Test Reference Tag field Write Error Handling triggered!!")
            
            logging.info("Test Reference Tag field Read Error Handling, Error reftag")
            read_result, data_read_back, mdata_read_back = adm_common.e2e_data_protection_nvme_read_test(slba, nlb, read_data_file, data_size, mdata_size, read_mdata_file, prinfo, reftag_error, apptag)
            if read_result == 0:
                logging.error("Test Reference Tag field Read Error Handling did not trigger")
                pytest.fail()
            else:
                logging.info("Test Reference Tag field Read Error Handling triggered!!")  
                 
        logging.info('test_E2e_data_protection_error_cases FINISH!')   
        test_flag = 0    
            
    @pytest.mark.timeout(method="signal")
    def test_E2e_data_protection_simple_but_include_all_pass_cases(self):
        global test_flag
        test_flag = -1
        lba_format_list = [5, 6, 12, 7 ,8 ,14] #5,6,12 meta 8b. 7,8,14 meta 16b
        pi_list = [1, 2, 3]
        pil_list = [0, 1]
        #nlb_list = [1+random.randint(1,1000), 1000+random.randint(1,10000), 10000+random.randint(1,100000)]
        #nlb_list = [1, 8]
        nlb_list = [1]
        #slba_list = [random.randint(1,1000), 1000+random.randint(1,10000), 10000+random.randint(1,100000)]
        #slba_list = [0, 8, 16]
        slba_list = [8]
        #######
        #prinfo = pract + prchk
        ##pract = 0000 or 1000 ->0 or 8
        ##prchk = 000, 001, 010, 011, 100, 101, 110, 111
        #######
        
        #pract = [0 ,8] #0: use self-defined metadata 1: use host-defined metadata
        pract_list = [8, 0]
        #prchk = [0, 1, 2, 3, 4, 5, 6, 7] # 1 is not accept now
        prchk_list = [0, 2, 4, 6 ] #bit 0 set to 0
        prchk_fail_list = [1, 3, 5, 7] #bit 0 set to 1
        result = False
        #Test metadata size = 8 bytes
        count = 1
        parameters = product(lba_format_list, pi_list, pil_list, nlb_list, slba_list)
        try:
            for parameter in parameters:
                lba_format, pi, pil, nlb, slba = parameter[0], parameter[1], parameter[2], parameter[3], parameter[4]
                #Test1. must PASS
                reftag = slba
                if pi != 3:
                    prchk_test_list = prchk_list + prchk_fail_list
                else:
                    prchk_test_list = prchk_list

                #Step1. Format drive
                format_result, byte_per_lba, byte_per_metadata = self.format(lba_format, pi, pil)
                if format_result == 'Fail':
                    logging.error('Format Failed with lba_format: {}, pi: {}, pil: {}, nlb: {}, slba: {}'.format(parameter[0], parameter[1], parameter[2], parameter[3], parameter[4]))
                    pytest.fail()       
                             
                for prchk in prchk_test_list:
                    host_defined_metadata_flag = True
                    #Step2. Prepare write, metadata
                    #logging.info("===========================START================================")
                    write_pattern = random.randint(1,9)
                    #logging.info("Write pattern: {}".format(write_pattern))
                    write_file = 'write_file.bin'
                    read_data_file = 'read_data.bin'
                    metadata_pattern = random.randint(1,9)
                    #logging.info("metadata pattern: {}".format(metadata_pattern))
                    metadata_file = 'metadata_file.bin'
                    read_mdata_file = 'read_mdata.bin'
                    apptag = random.randint(1,9)
                    byte_per_lba, byte_per_metadata = self.get_format_feature(lba_format)
                    write_data = adm_common.e2e_data_protection_create_dat_file_by_LBA(write_pattern, nlb, write_file, byte_per_lba)
                    metadata_data = adm_common.e2e_data_protection_create_dat_file_by_LBA(metadata_pattern, nlb, metadata_file, byte_per_metadata)
                    host_defind_mdata = []
                    for pract in pract_list:
                        data_size = nlb*byte_per_lba
                        mdata_size = nlb*byte_per_metadata
                        prinfo = pract + prchk
                        if host_defined_metadata_flag == False:
                            #logging.info('mv read_mdata.bin metadata_file.bin')
                            os.system("mv read_mdata.bin metadata_file.bin")
                            with open("metadata_file.bin","rb") as f:
                                metadata_data = f.read()
                                                                                    
                        #logging.info("Do Write Test")
                        write_result = adm_common.e2e_data_protection_nvme_write_test(slba, nlb, write_data, data_size, mdata_size, metadata_data, prinfo, reftag, apptag)
                        if write_result != 0:
                            logging.error('Write Failed')
                            pytest.fail()
                            
                        #logging.info("Sleep 10 sec")
                        time.sleep(10)
                        #logging.info("Do Read Test")
                        if prinfo >= 8: 
                            prinfo_read = prinfo-8
                        #logging.info("read_prinfo {}".format(prinfo_read))
                        read_result, data_read_back, mdata_read_back = adm_common.e2e_data_protection_nvme_read_test(slba, nlb, read_data_file, data_size, mdata_size, read_mdata_file, prinfo_read, reftag, apptag)
                        if read_result != 0:
                            logging.error('Read Failed')
                            pytest.fail() 
    
                        for i in range(len(data_read_back)):
                            if int(write_data[i]) != int(data_read_back[i]):
                                logging.error('Data compare Failed')
                                logging.error('Data:{} expect:{}, real:{}'.format(i, write_data[i], data_read_back[i]))
                                pytest.fail() 
                        #logging.info("Data compare PASS")
    
                        if host_defined_metadata_flag == True:
                            host_defined_metadata_flag = False
                            #logging.info("Use host defined metadata, don't need to compare mdata")
                            host_defind_mdata.append(mdata_read_back)
                        else:
                            #logging.info("Compare metadata")
                            for i in range(len(mdata_read_back)):
                                if int(host_defind_mdata[0][i]) != int(mdata_read_back[i]):
                                    logging.error('Metadata compare Failed')
                                    logging.error('Data:{} expect:{}, real:{}'.format(i,host_defind_mdata[0][i], mdata_read_back[i]))
                                    pytest.fail() 
                            #logging.info("Data compare PASS")
                            
                        #slba += 8
                        #reftag = slba
                    logging.info('Test Count: {} PASS'.format(count))
                    count += 1
                    #logging.info("============================END=================================")
            result = True              
        except Exception as e:
            logger.error("Exception met during {} basic test:{}".format(function, e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
            logging.info("==============================")
            logging.info("Write pattern: {}".format(write_pattern))
            logging.info("metadata pattern: {}".format(metadata_pattern))
            logging.info("lba_format {}".format(lba_format))
            logging.info("slba {}".format(slba))
            logging.info("nlb {}".format(nlb))
            logging.info("pi {}".format(pi))
            logging.info("pil {}".format(pil))
            logging.info("byte_per_lba {}".format(byte_per_lba))
            logging.info("byte_per_metadata {}".format(byte_per_metadata))
            logging.info("data_size {}".format(data_size))
            logging.info("mdata_size {}".format(mdata_size))
            logging.info("reftag {}".format(reftag))
            logging.info("write_prinfo {}".format(prinfo))
            logging.info("apptag: {}".format(apptag))
            logging.info("==============================")
        finally:
            if result != True:
                logging.error('test_E2e_data_protection_simple_but_include_all_pass_cases Failed')
                pytest.fail() 
            test_flag = 0
                            
    @pytest.mark.timeout(method="signal")
    def test_E2e_data_protection_diffcult_but_random_choose_pass_cases(self):
        global test_flag
        lba_format_list = [5, 6, 12, 7 ,8 ,14] #5,6,12 meta 8b. 7,8,14 meta 16b
        pi_list = [1, 2, 3]
        pil_list = [0, 1]
        nlb_list = [1+random.randint(1,1000), 1000+random.randint(1,10000), 10000+random.randint(1,100000)]
        #nlb_list = [1, 8]
        nlb_list = [1]
        #slba_list = [random.randint(1,1000), 1000+random.randint(1,10000), 10000+random.randint(1,100000)]
        #slba_list = [0, 8, 16]
        slba_list = [128, 4096, 40960, 49152]
        test_flag = -1
        #######
        #prinfo = pract + prchk
        ##pract = 0000 or 1000 ->0 or 8
        ##prchk = 000, 001, 010, 011, 100, 101, 110, 111
        #######
        
        #pract = [0 ,8] #0: use self-defined metadata 1: use host-defined metadata
        pract_list = [8, 0]
        #prchk = [0, 1, 2, 3, 4, 5, 6, 7] # 1 is not accept now
        prchk_list = [0, 2, 4, 6 ] #bit 0 set to 0
        prchk_fail_list = [1, 3, 5, 7] #bit 0 set to 1
        result = False
        #Test metadata size = 8 bytes
        count = 1
        parameters = product(lba_format_list, pi_list, pil_list, nlb_list, slba_list)
        try:
            for parameter in parameters:
                test_or_not = random.randint(0,10)
                #Random choose 
                if test_or_not > 1:
                    continue
                lba_format, pi, pil, nlb, slba = parameter[0], parameter[1], parameter[2], parameter[3], parameter[4]
                #Test1. must PASS
                reftag = slba
                if pi != 3:
                    prchk_test_list = prchk_list + prchk_fail_list
                else:
                    prchk_test_list = prchk_list

                #Step1. Format drive
                format_result, byte_per_lba, byte_per_metadata = self.format(lba_format, pi, pil)
                if format_result == 'Fail':
                    logging.error('Format Failed with lba_format: {}, pi: {}, pil: {}, nlb: {}, slba: {}'.format(parameter[0], parameter[1], parameter[2], parameter[3], parameter[4]))
                    pytest.fail()       
                             
                for prchk in prchk_test_list:
                    host_defined_metadata_flag = True
                    #Step2. Prepare write, metadata
                    #logging.info("===========================START================================")
                    write_pattern = random.randint(1,9)
                    #logging.info("Write pattern: {}".format(write_pattern))
                    write_file = 'write_file.bin'
                    read_data_file = 'read_data.bin'
                    metadata_pattern = random.randint(1,9)
                    #logging.info("metadata pattern: {}".format(metadata_pattern))
                    metadata_file = 'metadata_file.bin'
                    read_mdata_file = 'read_mdata.bin'
                    apptag = random.randint(1,9)
                    byte_per_lba, byte_per_metadata = self.get_format_feature(lba_format)
                    write_data = adm_common.e2e_data_protection_create_dat_file_by_LBA(write_pattern, nlb, write_file, byte_per_lba)
                    metadata_data = adm_common.e2e_data_protection_create_dat_file_by_LBA(metadata_pattern, nlb, metadata_file, byte_per_metadata)
                    host_defind_mdata = []
                    for pract in pract_list:
                        data_size = nlb*byte_per_lba
                        mdata_size = nlb*byte_per_metadata
                        prinfo = pract + prchk
                        if host_defined_metadata_flag == False:
                            #logging.info('mv read_mdata.bin metadata_file.bin')
                            os.system("mv read_mdata.bin metadata_file.bin")
                            with open("metadata_file.bin","rb") as f:
                                metadata_data = f.read()
                                                                                    
                        #logging.info("Do Write Test")
                        write_result = adm_common.e2e_data_protection_nvme_write_test(slba, nlb, write_data, data_size, mdata_size, metadata_data, prinfo, reftag, apptag)
                        if write_result != 0:
                            logging.error('Write Failed')
                            pytest.fail()
                            
                        #logging.info("Sleep 10 sec")
                        time.sleep(10)
                        #logging.info("Do Read Test")
                        if prinfo >= 8: 
                            prinfo_read = prinfo-8
                        #logging.info("read_prinfo {}".format(prinfo_read))
                        read_result, data_read_back, mdata_read_back = adm_common.e2e_data_protection_nvme_read_test(slba, nlb, read_data_file, data_size, mdata_size, read_mdata_file, prinfo_read, reftag, apptag)
                        if read_result != 0:
                            logging.error('Read Failed')
                            pytest.fail() 
    
                        for i in range(len(data_read_back)):
                            if int(write_data[i]) != int(data_read_back[i]):
                                logging.error('Data compare Failed')
                                logging.error('Data:{} expect:{}, real:{}'.format(i, write_data[i], data_read_back[i]))
                                pytest.fail() 
                        #logging.info("Data compare PASS")
    
                        if host_defined_metadata_flag == True:
                            host_defined_metadata_flag = False
                            #logging.info("Use host defined metadata, don't need to compare mdata")
                            host_defind_mdata.append(mdata_read_back)
                        else:
                            #logging.info("Compare metadata")
                            for i in range(len(mdata_read_back)):
                                if int(host_defind_mdata[0][i]) != int(mdata_read_back[i]):
                                    logging.error('Metadata compare Failed')
                                    logging.error('Data:{} expect:{}, real:{}'.format(i,host_defind_mdata[0][i], mdata_read_back[i]))
                                    pytest.fail() 
                            #logging.info("Data compare PASS")
                            
                        #slba += 8
                        #reftag = slba
                    logging.info('Test Count: {} PASS'.format(count))
                    count += 1
                    #logging.info("============================END=================================")
            result = True              
        except Exception as e:
            logger.error("Exception met during {} basic test:{}".format(function, e))
            logger.info("Exception in {}, line: {}".format(e.__traceback__.tb_frame.f_globals["__file__"], e.__traceback__.tb_lineno))
            logging.info("==============================")
            logging.info("Write pattern: {}".format(write_pattern))
            logging.info("metadata pattern: {}".format(metadata_pattern))
            logging.info("lba_format {}".format(lba_format))
            logging.info("slba {}".format(slba))
            logging.info("nlb {}".format(nlb))
            logging.info("pi {}".format(pi))
            logging.info("pil {}".format(pil))
            logging.info("byte_per_lba {}".format(byte_per_lba))
            logging.info("byte_per_metadata {}".format(byte_per_metadata))
            logging.info("data_size {}".format(data_size))
            logging.info("mdata_size {}".format(mdata_size))
            logging.info("reftag {}".format(reftag))
            logging.info("write_prinfo {}".format(prinfo))
            logging.info("apptag: {}".format(apptag))
            logging.info("==============================")
        finally:
            if result != True:
                logging.error('test_E2e_data_protection_diffcult_but_random_choose_pass_cases Failed')
                pytest.fail() 
            test_flag = 0

    def test_E2e_data_protection_revert_to_default_lba(self):
        global test_flag
        test_flag = -1
        logging.info("Return to default format: LBAF1")
        erase_drive = 1
        test_flag = adm_common.format(int(1), erase_drive, 'vail')
        
        if test_flag != 0:
            logging.error("Return to default format: LBAF1 FAILED")
            pytest.fail() 

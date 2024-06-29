#!/usr/bin/python
import pytest
from configparser import ConfigParser
import os
import subprocess
import time
import logging
import glob
import copy
from data_analyzer import Data_Analyzer
import sys
sys.path.append("../")
from common import fvt_adm_cmd_common

logging.basicConfig(level=logging.INFO,format='[%(asctime)s.%(msecs)03d] %(levelname)s %(filename)s(line:%(lineno)d): %(message)s')

cfg_file = "./fio_cfg.txt"

class CaseGenerator():
    def get_case_fio(self, list_all, key):
        '''
        get cotent for each part seperated by []
        the configure file should contain a [global] part at the beginning
        '''
        case_all = []
        list_tmp = []
        flag = 0
        for el in list_all:
            if key not in el and el != '\n':
                list_tmp.append("--"+el.strip('\n'))  # store option in a list with -- added before
                continue
            # for first section, i.e. global in fio, just option added, no need for the [global] mark
            elif key in el and flag == 0:
                flag = flag + 1
                continue
            elif key in el and flag != 0:
                case_all.append(list_tmp)
                list_tmp = [el.strip('\n').strip('[]')]  # content in [] as case name
                continue
        case_all.append(list_tmp)
        return case_all

    def generate_case_fio(self, filename, lba_size, params):
        '''
        generate option list for each case by combining global and specific part
        the case name is the first element of each list
        params: configured fio params from fio_cfg, [runtime, qd, io_size, block_align, loop, thread, offset]
        lba_size: sector size that the drive formatted at
        '''
        file = open(filename, 'r')
        list_all = []
        runtime = params[0]
        qd = params[1]
        io_size = params[2]
        block_align = params[3]
        loop = params[4]
        thread = str(params[5]) # if no specified, default is 1
        offset = params[6]

        for line in file:
            if "#" not in line:
                list_all.append(line)
        file.close()
        case_all = self.get_case_fio(list_all, '[')  # for fio, [] used for each configure
        opt_list = []
        opt_tmp = []
        
        for i in range(len(case_all)):
            if i > 0:
                case_name = case_all[i][0] # first element for case name
                global_option = case_all[0] # option in global part
                options = case_all[i][1:] # option in each case
                offset_flag = 0 # to avoid duplicated config if offset is specified in .fio, i.e. not accept from fio_cfg

                for ot in offset:
                    if offset_flag == 1:
                        break
                    if ot.lower() == '0':
                        align_flag = "aligned"  # just used for case name
                    else:  # 512b as unaligned
                        align_flag = "unaligned"
                    if "$QD" in case_name and "$BS" not in case_name:
                        if len(qd) == 0:
                            logging.error("You need to specify io depth in cfg file")
                            pytest.fail("You need to specify io depth in cfg file")
                        for q in qd:
                            opt_tmp.append(global_option)
                            new_opt_list = copy.deepcopy(options)
                            thread = get_accurate_value(new_opt_list, "numjobs", thread)
                            opt_tmp.append(case_name.replace("$QD", thread + "x" + q) + "_sectorsize_" + lba_size + "_" + align_flag)
                            # opt_tmp.extend(global_option)
                            offset_flag = update_config(new_opt_list, "offset", ot, opt_tmp) 
                            update_config(new_opt_list, "iodepth", q, opt_tmp) 
                            update_config(new_opt_list, "runtime", runtime, opt_tmp)   
                            update_config(new_opt_list, "numjobs", thread, opt_tmp)  
                            #update_config(new_opt_list, "blockalign", aligned, opt_tmp)    
                            update_config(new_opt_list, "loop", loop, opt_tmp)  
                            opt_tmp.extend(new_opt_list) 
                            opt_list.append(opt_tmp)
                            opt_tmp = []   
                    elif "$QD" not in case_name and "$BS" in case_name:
                        if len(io_size) == 0:
                            logging.error("You need to specify io size in cfg file")
                            pytest.fail("You need to specify io size in cfg file")
                        for size in io_size:
                            opt_tmp.append(global_option)
                            new_opt_list = copy.deepcopy(options)
                            opt_tmp.append(case_name.replace("$BS", size) + "_sectorsize_" + lba_size + "_" + align_flag)
                            # opt_tmp.extend(global_option)
                            update_config(new_opt_list, "bs", size, opt_tmp)
                            offset_flag = update_config(new_opt_list, "offset", ot, opt_tmp) 
                            update_config(new_opt_list, "runtime", runtime, opt_tmp)    
                            update_config(new_opt_list, "numjobs", thread, opt_tmp) 
                            #update_config(new_opt_list, "blockalign", aligned, opt_tmp)    
                            update_config(new_opt_list, "loop", loop, opt_tmp)  
                            opt_tmp.extend(new_opt_list) 
                            opt_list.append(opt_tmp)
                            opt_tmp = [] 
                    elif "$QD" in case_name and "$BS" in case_name:
                        if len(qd) == 0 or len(io_size) == 0:
                            logging.error("You need to specify io depth/size in cfg file")
                            pytest.fail("You need to specify io depth/size in cfg file")
                        for q in qd:
                            for size in io_size:
                                opt_tmp.append(global_option)
                                new_opt_list = copy.deepcopy(options)
                                thread = get_accurate_value(new_opt_list, "numjobs", thread)
                                opt_tmp.append(case_name.replace("$QD", thread + "x" + q).replace("$BS", size) + "_sectorsize_" + lba_size + "_" + align_flag)
                                # opt_tmp.extend(global_option)
                                offset_flag = update_config(new_opt_list, "offset", ot, opt_tmp) 
                                update_config(new_opt_list, "iodepth", q, opt_tmp) 
                                update_config(new_opt_list, "bs", size, opt_tmp)
                                update_config(new_opt_list, "runtime", runtime, opt_tmp)   
                                update_config(new_opt_list, "numjobs", thread, opt_tmp)  
                                #update_config(new_opt_list, "blockalign", aligned, opt_tmp)    
                                update_config(new_opt_list, "loop", loop, opt_tmp)
                                opt_tmp.extend(new_opt_list) 
                                opt_list.append(opt_tmp)
                                opt_tmp = [] 
                    else:
                        opt_tmp.append(global_option)
                        new_opt_list = copy.deepcopy(options)
                        opt_tmp.append(case_name + "_sectorsize_" + lba_size + "_" + align_flag)
                        # opt_tmp.extend(global_option)
                        offset_flag = update_config(new_opt_list, "offset", ot, opt_tmp) 
                        update_config(new_opt_list, "runtime", runtime, opt_tmp)    
                        update_config(new_opt_list, "numjobs", thread, opt_tmp) 
                        #update_config(new_opt_list, "blockalign", aligned, opt_tmp)    
                        update_config(new_opt_list, "loop", loop, opt_tmp)  
                        opt_tmp.extend(new_opt_list) 
                        opt_list.append(opt_tmp)
                        opt_tmp = []              
        logging.debug("case config list: {}".format(opt_list))
        return opt_list
        #example: [['seqwr_128k_iodepth_32', '--runtime=120', '--stonewall']
        # ['seqwr_64k_iodepth_32', '--runtime=120']]

def get_cfg(config_file, case_suite, lba_size):
    '''
    get the config file for specific test suite from the global config file.
    config_file: "./fio_cfg.txt", fixed in this script (at the top)
    case_suite: test suite: precommit, postcommit or nightly
    lba_size: formated lba size, to seperate blockalign and offset params for FIO
    return: configFile from fio config, timeout of each fio test case
    '''
    config = ConfigParser()
    config.read(config_file)
    qd = []
    io_size = []
    block_align = [] # deprecated for now
    runtime = None
    thread = 1 # for use case name if no such value specified, for ex. 1x512
    offset = ["0"]
    # There're already below 3 items in cfg
    configFile = config.get("Fio", case_suite).strip()
    timeout = config.get('Fio', case_suite+'_timeout').strip()
    loop = 1

    try:
        runtime = config.get('Fio', case_suite+'_runtime').strip()
    except Exception as e:
        logging.debug("No runtime configured")

    try:
        thread = config.get('Fio', case_suite+'_thread').strip()
    except Exception as e:
        logging.debug("No thread num configured")

    try:
        qd = config.get('Fio', case_suite+'_qd').split(',')
        qd = [i.strip() for i in qd]
    except Exception as e:
        logging.debug("No qd configured")

    try:
        io_size = config.get('Fio', case_suite+'_io_size').split(',')
        io_size = [i.strip() for i in io_size]
    except Exception as e:
        logging.debug("No io size configured")

    try:
        offset = config.get('Fio', case_suite+'_offset').split(',')
        offset = [i.strip() for i in offset]
    except Exception as e:
        logging.debug("No offset configured")

    try:
        block_align = config.get('Fio', case_suite + '_blockalign_' + lba_size).split(',')
        block_align = [i.strip() for i in block_align]
    except Exception as e:
        logging.debug("No block align configured")

    if case_suite == 'performance':
        try:
            loop = config.get('Fio', case_suite+'_loop').strip()
        except Exception as e:
            logging.info("No loop configured, default to 1")
    return configFile, [timeout, runtime, qd, io_size, block_align, loop, thread, offset]

def update_config(option_list, option, new_value, opt_tmp):
    '''
    update option in option_list and remove from list.
    for ex, --runtime=test to runtime=new_value
    option_list: list of all options, like [--time_base, runtime=100]
    option: option name, such as runtime
    new_value: value to be set to option
    '''
    try:
        for op in option_list:
            if new_value != None:
                if option in op:
                    if "$" not in op:
                        logging.debug("You specified an accurate value, thus no need to replace it")
                        # return 1
                    else:
                        new_option = op.split("=")[0] + "=" + new_value
                        option_list.remove(op)
                        opt_tmp.append(new_option)
                        # break
        else:
            logging.debug("No item found or no value specified, thus no value changed: {}".format(option))
    except Exception as e:
        logging.warning("Update failed: {}".format(e))

def get_accurate_value(option_list, option, default_value):
    '''
    option_list: list of all options, like [--numbjobs=4, runtime=100]
    option: option name, such as numjobs
    default_value: if no accurate value returned, set to default value
    Currently used to get numjobs used in case name if the value is spcified in .fio config file and not replaced by external value
    '''
    accurate_value = None
    for op in option_list:
        if option in op:
            if "$" not in op:
                logging.debug("You specified an accurate value, thus no need to replace it")
                accurate_value = op.split("=")[1].strip()
                break
    else:
        accurate_value = default_value
    return accurate_value

def pytest_generate_tests(metafunc):
    '''
    pytest build-in hook, used to parametrize the fio configure file to a list for loop run
    '''
    idlist = []
    argvalues = []
    params = []
    case = metafunc.config.getoption('case_suite')
    lba_size = metafunc.config.getoption('lba_size')
    configFile, params = get_cfg(cfg_file, case, lba_size)
    timeout = params[0]
    cg = CaseGenerator()
    config_list = cg.generate_case_fio(configFile, lba_size, params[1:])  # para for getoption is the dest of each addoption

    for case in config_list:
        # optimization: global options seperately recorded, for mixed jobs seperated by name option
        idlist.append(case[1])
        argvalues.append(case[0:])  # also pass the first element which is the case id to test function, used for log
    metafunc.parametrize('fio_config', argvalues, ids=idlist)  # ids for case id
    metafunc.parametrize('timeout', [timeout])  # ids for case id

def execute_cmd(cmd, timeout, out_flag = False, expect_fail = False, expect_err_info = None):
	'''
	Execute cmd in #timeout seconds
	out_flag: True means return cmd out(a str list), Flase not.
	expect_fail: for some error inject scenario, set this to True
	expect_err_info: if expect failure, then check the error msg as expected or not
	'''
	logging.info(cmd)
	result = 0
	try:
		p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell = True) 
		t_beginning = time.time()
		seconds_passed = 0 
		while True:
			if p.poll() is not None: 
				out = p.stdout.readlines()
				out = [i.decode().strip("\n") for i in out]  # convert to string
				if p.returncode == 0:
					logging.info("Cmd executed successfully")
				elif p.returncode != 1:  # specified scenario: nvme list | grep nvme, if nothing returned, the returncode is 1, it seems caused by the grep, for ex. ls | grep leon, if nothing found, returncode is 1
					logging.info("Cmd output: {}".format(out[0]))  # just show the first out to avoid too many logs
					if expect_fail:
						logging.info("Cmd executed failed, but it's as expected")
						result = 0
						if expect_err_info != None and expect_err_info not in out[0]:
							logging.warning("Error msg not as expected, you may have a check")
					else:
						logging.error("Cmd executed failed")
						result = -1
				break 
			time.sleep(1)
			seconds_passed = time.time() - t_beginning 
			if seconds_passed > timeout: 
				p.stdout.close()
				if "fio" in cmd:
					os.system("pkill -9 fio")
				p.terminate()
				logging.error('Cmd not end as expected in {} seconds, terminate it.'.format(timeout))
				logging.warning('This might be caused by low performance if no abnormal in fw log.')
				result = -1
				break
		p.stdout.close()
	except Exception as e:
		logging.error("Cmd execution failed: {}".format(e))
		result = -1
	if out_flag == False:
		return result
	else:
		return result, out

class TestFio():
    @pytest.fixture(scope='class')
    def log_folder(self, hostname, mofify_folder_name):
        '''
        setup for the whole class: clear former logs and create new folder for logs
        '''
        global flag  # flag used to check if the last test failed
        flag = 0
        if mofify_folder_name == 'False':
            folder_name = hostname+"_FIO_logs"
        else:
            folder_name = hostname+ "_"+ mofify_folder_name +"_FIO_logs"

        # TestBed folder has been cleaned up during testbed_cp process, plus need to run test for different lba_size.
        # if os.path.exists(folder_name):
        #     shutil.rmtree(folder_name)
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        log_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), folder_name)
        yield log_folder
        expected = glob.glob('*.expected')
        received = glob.glob('*.received')
        if expected:
            for ext in expected:
                os.system('sudo mv {} {}'.format(ext, log_folder))
        if received:
            for recv in received:
                os.system('sudo mv {} {}'.format(recv, log_folder))

    @pytest.fixture(scope='function')
    def log(self, log_folder, fio_config):
        '''
        setup for each test, runtime log with case name
        '''
        fio_logname = "fio_"+str(fio_config[1])+".log"  # case name is the second element of fio_config, the 1st the the list of global params
        fio_log = log_folder + '/' + fio_logname
        yield fio_log

    @pytest.fixture(scope='class')
    def result_summary(self, log_folder, perf):
        '''
        Create a summary log for fio test cases
        '''
        summary_file = log_folder + '/FIO_result.log'
        perf_result = None
        if perf == "True": 
            perf_result = log_folder + "/FIO_perf.log"
            if os.path.exists(perf_result):
                os.system("mv {} {}".format(perf_result, log_folder + "/FIO_perf_last.log"))
        yield summary_file, perf_result

    def test_fio(self, log, fio_config, timeout, result_summary, dry_run, perf, controller, namespace, pytestconfig, need_format):
        '''
        Main body of the fio test
        Para:
        log: the setup function to get the fio log
        fio_config: fio config got from config file
        '''
        global flag
        case_suite = pytestconfig.getoption('--case_suite')
        summary_file, perf_result = result_summary
        if flag == -1:
            logging.error("FIO test failed.")
            pytest.exit('Fio test failed!')
        if (perf == "True" or need_format == "True") and "wr" in fio_config[1] and 'ramdrive' not in case_suite : #nvme format before write perf tests
            adm_common = fvt_adm_cmd_common.fvt_adm(controller, namespace)
            ret = adm_common.format(1, 0, 'vail')
            if ret != 0:
                logging.error("NVMe format failed") 
                pytest.fail("NVMe format failed") 
        time.sleep(5)  # temperary for vail to flush
        global_option = " ".join(fio_config[0][0:])
        job = '--name ' + fio_config[1]
        option = " ".join(fio_config[2:])
        cmd = "sudo fio {0} {1} {2} --output={3}".format(global_option, job, option, log)
        # logging.info(cmd)
        if dry_run:
            pytest.skip()
 
        if execute_cmd(cmd, int(timeout)) != 0:
            with open(summary_file, 'a+') as f:
                f.write('%-25s:%-35s\n' % (fio_config[1], 'Fail'))
            flag = -1
            logging.error("FIO test failed.")
            pytest.fail("FIO test failed") 
                        
        result = self.check_result(log)

        with open(summary_file, 'a+') as f:
            f.write('%-25s:%-35s\n' % (fio_config[1], result))

        if result == 'Pass' and perf_result != None and "precondition" not in fio_config[1]:
            logging.info("Collect and record performance data")
            Data_Analyzer(log, perf_result, fio_config[1]).get_perf_data()

        if result != 'Pass':
            flag = -1
            logging.error("FIO test failed.")
            pytest.fail('Fio test failed!')

    def check_result(self, log_file, pattern = "err="):
        logging.info("Checking fio result: {}".format(log_file))
        result = 'Pass'
        flag = 0  # if no err= info in output file
        if os.path.exists(log_file):
            with open(log_file, 'r') as processLog:
                while True:
                    entry = processLog.readline()
                    if pattern in entry:
                        flag = 1
                        if pattern + " 0" in entry:
                            result = "Pass"  # there might be several result, for ex. Mixed RW
                        else:
                            result = "Fail"
                            break
                    elif entry == '':
                        if flag == 0:
                            logging.info("No result info found, FIO test failed")
                            result = "Fail"
                        break
        else:
            logging.error("No fio log found:{}".format(log_file))
            result = "Fail"
        if result == "Pass":
            logging.info("Fio test passed")
        else:
            logging.info("Fio test failed")
        return result

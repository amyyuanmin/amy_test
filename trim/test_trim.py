import sys
import time
import os
import subprocess
import re
import pytest
import logging

logger = logging.basicConfig(filename='trim_debug.log', filemode='w', level=logging.DEBUG)
logger = logging.basicConfig(format='%(message)s')
logger = logging.getLogger("TrimTestRunner")


_CMD_DETECT_NVME = "ls /dev/nvme0"
_CMD_NVME_LIST = "sudo nvme list"
_CMD_LS_NVME_DEVICES = "ls -l /dev/nvm*"

LBN_SIZE = 4096
MAX_CMD_LBA_COUNT = 32

WRITE_4k_PATTERN = [0xaa for i in range(LBN_SIZE)]
WRITE_128k_PATTERN = [0xaa for i in range(LBN_SIZE * MAX_CMD_LBA_COUNT)]

TRIM_4K_PATTERN = [0x00 for i in range(LBN_SIZE)]
TRIM_128K_PATTERN = [0x00 for i in range(LBN_SIZE * MAX_CMD_LBA_COUNT)]

SLEEP_TIME = 1

OK = 0
FAIL = 1
EXCEPTION_OCCURRED = 2

def _post_send_command_actions(command, exp_rc, out, err, rc):
    """Process command result output.

    Args:
        command (str): Shell or bash command
        exp_rc (list): Expected result
        out (byte): Console output
        err (byte): Stderr output
        rc (int): Result code

    Returns:
        (tuple): Formatted command output and error output
    """
    out1 = out.decode('utf-8').rstrip('\n').split('\n')
    err1 = err.decode('utf-8').rstrip('\n').split('\n')

    logger.debug("Output stream:")
    for line in out1:
        logger.debug("        |" + line)

    logger.debug("Error stream:")

    for line in err1:
        logger.debug("        |" + line)
    logger.debug("Command result: {0}".format(rc))

    if exp_rc is not None and not isinstance(exp_rc, list):
        exp_rc = [int(exp_rc)]
    elif exp_rc is not None:
        exp_rc = [int(item) for item in exp_rc]

    if exp_rc is not None:
        if rc not in exp_rc:
            raise AssertionError(
                "Error occurred  during '%s' execution: "
                "got rc='%s' but expected %s. %s " % (
                    command, rc, exp_rc, err1))
    return out1, err1

def subprocess_send_command(command, exp_rc=0, timeout=None):
    """Send command via shell.

    Args:
        command (str): Shell or bash command
        exp_rc (int): expected result, 0 by default
        timeout (int): timeout to kill communicate process

    Returns: output , error output , result


    """

    logger.debug(
        "Executing command %s , expecting rc %s..." % (
            command, exp_rc))
    sub_process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    try:
        out, err = sub_process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        sub_process.kill()
        out, err = sub_process.communicate()
        rc = sub_process.returncode
        _post_send_command_actions(command, None, out, err, rc)
        raise
    rc = sub_process.returncode
    logger.debug("Command executed.")
    out1, err1 = _post_send_command_actions(command, exp_rc, out, err, rc)
    return out1, err1, rc

def send_command_with_output_logging(command):
    out = subprocess_send_command(command)
    for _ in out[0]:
        print(_)

def console_out(out1, err1):
    if out1[0] and out1[0] != '1':
        print('{}'.format(out1[0]))
    if err1[0]:
        print('{}'.format(err1[0]))

def get_nvme_lba_size():
    process = subprocess.Popen(["sudo", "nvme", "id-ns", "/dev/nvme0n1", "-H"], stdout=subprocess.PIPE)
    out, err = process.communicate()

    # search lba size from nvme driver interface output
    lba_size = 0
    if b'Data Size:' in out:
        # e.g."LBA Format  0 : Metadata Size: 0   bytes - Data Size: 4096 bytes - Relative Performance: 0 Best (in use)"
        z = re.search('Data Size: (\d+) ', str(out))
        lba_size = (int)(z.group(1))
        print("lba size in bytes: {}".format(lba_size))
    else:
        raise RuntimeError("TrimTest: test FAILED. LBA size not defined")

    return lba_size

def write_data_pattern(lbn_count):
    remaining_blocks = lbn_count

    patternArray_4k = bytearray(WRITE_4k_PATTERN)
    patternArray_128k = bytearray(WRITE_128k_PATTERN)

    f = open("/dev/nvme0n1", "wb")
    while remaining_blocks > 0:
        # set position in file
        f.seek((lbn_count - remaining_blocks) * LBN_SIZE, 0)

        if remaining_blocks >= MAX_CMD_LBA_COUNT:
            patternArray = patternArray_128k
            remaining_blocks = remaining_blocks - MAX_CMD_LBA_COUNT
        else:
            patternArray = patternArray_4k
            remaining_blocks = remaining_blocks - 1

        f.write(patternArray)

    f.close()

def read_and_verify_data_pattern(lbn_count, verify_type):
    result = OK
    remaining_blocks = lbn_count

    f = open("/dev/nvme0n1", "rb")

    while remaining_blocks > 0:
        # set position in file
        f.seek((lbn_count - remaining_blocks) * LBN_SIZE, 0)

        if remaining_blocks >= MAX_CMD_LBA_COUNT:
            data_size = LBN_SIZE * MAX_CMD_LBA_COUNT
            remaining_blocks = remaining_blocks - MAX_CMD_LBA_COUNT
            # choose pattern to verify
            if verify_type == "write":
                verify_pattern = bytearray(WRITE_128k_PATTERN)
            else:
                verify_pattern = bytearray(TRIM_128K_PATTERN)
        else:
            data_size = LBN_SIZE
            remaining_blocks = remaining_blocks - 1
            # choose pattern to verify
            if verify_type == "write":
                verify_pattern = bytearray(WRITE_4k_PATTERN)
            else:
                verify_pattern = bytearray(TRIM_4K_PATTERN)

        data = f.read(data_size)
        if data != verify_pattern:
            print("remaining blocks: {}".format(remaining_blocks))
            print("read: {}".format(data[0]))
            print("verify: {}".format(verify_pattern[0]))
            print("TrimTest: test FAILED. Files are not equal. Remaining blocks: {}".format(remaining_blocks))
            result = FAIL
            break

    f.close()
    return result


def trim_data(lbn_count):
#    str1 = "sudo nvme dsm /dev/nvme0 --namespace-id=1 -d --blocks=100000 --slbs=0"
    str1 = "sudo nvme dsm /dev/nvme0 --namespace-id=1 -d --blocks={} --slbs=0".format(lbn_count)
    out1, err1, rc = subprocess_send_command(str1)
    console_out(out1, err1)



def run_device_trim_test(lba_count):
    result = OK
    lba_size = get_nvme_lba_size()

    try:
        lba_count = int(lba_count)
        lbn_count = int((lba_count * lba_size) / LBN_SIZE)
        print("LBN count = {}".format(lbn_count))

        print("write pattern - \t{}".format(time.strftime("%H:%M:%S")))
        write_data_pattern(lbn_count)
        
        print("read pattern - \t\t{}".format(time.strftime("%H:%M:%S")))
        result = read_and_verify_data_pattern(lbn_count, "write")
        
        if result == OK:
            print("trim blocks - \t\t{}".format(time.strftime("%H:%M:%S")))
            trim_data(lbn_count)
            time.sleep(2*SLEEP_TIME)

            print("read trim pattern - \t{}".format(time.strftime("%H:%M:%S")))
            result = read_and_verify_data_pattern(lbn_count, "trim")

        print("test finished - \t{}".format(time.strftime("%H:%M:%S")))

        time.sleep(SLEEP_TIME)
        
    except Exception as e:
        print(e)
        result = EXCEPTION_OCCURRED


    return result
#
def load_nvme_driver():
    print("Load nvme driver")
    time.sleep(SLEEP_TIME)
    # load nvme. fail if cannot load
    subprocess_send_command("sudo modprobe nvme")
    time.sleep(SLEEP_TIME)
    print("Check to see if /dev/nvme0 is detected")
    # check if dut exists
    proc = subprocess.Popen(["ls", "/dev/nvme0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if err != b'':
        print("/dev/nvme0 is missing. ")
        raise RuntimeError("NVME Device was not detected! Exiting with failure")
    print("Check to see if nvme device is found in the list")
    process = subprocess.Popen(["sudo", "nvme", "list"], stdout=subprocess.PIPE)
    out, err = process.communicate()
    if "No NVMe devices" in str(out):
        print("NVME Device was not detected! Exiting with failure")
        raise RuntimeError("NVME Device was not detected in the list! Exiting with failure")
    print("NVMe device is detected")


class TestTrim():

    @pytest.mark.parametrize("lba_count", ["100000"])
    def test_trim(self, lba_count):
        print ("\n")
        print("Execute...trim for {} lba's".format(lba_count))
        subprocess.run(["nvme version"], check=False, shell=True)
        load_nvme_driver()

        print("List Controllers before IO tests")
        send_command_with_output_logging(_CMD_NVME_LIST)
        send_command_with_output_logging(_CMD_LS_NVME_DEVICES)

        result = run_device_trim_test(lba_count)
        
        if result == OK:
            print("Trim Test: PASSED\n")
        else:
            pytest.fail("Trim Test: FAILED\n")


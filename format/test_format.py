import sys
import time
import os
import subprocess
import re
import pytest
import logging

logger = logging.basicConfig(filename='format_debug.log', filemode='w', level=logging.DEBUG)
logger = logging.basicConfig(format='%(message)s')
logger = logging.getLogger("FormatTestRunner")

_CMD_DETECT_NVME = "ls /dev/nvme0"
_CMD_NVME_LIST = "sudo nvme list"
_CMD_LS_NVME_DEVICES = "ls -l /dev/nvm*"

LBN_SIZE = 4096

# write 24 LBNs because FTL makes physical write by 24 LBNs
# because of geometry of NAND chip
LBN_TO_VERIFY = 24

WRITE_4k_PATTERN = [0xaa for i in range(LBN_SIZE)]
TRIM_4K_PATTERN  = [0x00 for i in range(LBN_SIZE)]

SLEEP_TIME = 1

OK = 0
FAIL = 1
EXCEPTION_OCCURRED = 2

def console_out(out1, err1):
    if out1[0] and out1[0] != '1':
        print('{}'.format(out1[0]))
    if err1[0]:
        print('{}'.format(err1[0]))

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

def get_nvme_drive_size_in_lbn():
    process = subprocess.Popen(["sudo", "nvme", "id-ctrl", "/dev/nvme0"], stdout=subprocess.PIPE)
    out, err = process.communicate()

    if b'tnvmcap' in out:
        # e.g."tnvmcap : 4194304"
        z = re.search('tnvmcap\s*:\s*(\d+)', str(out))
        size = (int)(z.group(1))
        size = (size / LBN_SIZE)
        size = int(size)
        print("Drive size in LBNs: {}".format(size))
    else:
        raise RuntimeError("Format Test: FAILED. NS size not defined")
    return size

def write_data_pattern(lbn_count):
    remaining_blocks = lbn_count

    patternArray_4k = bytearray(WRITE_4k_PATTERN)

    f = open("/dev/nvme0n1", "wb")
    while remaining_blocks > 0:
        # set position in file
        f.seek((lbn_count - remaining_blocks) * LBN_SIZE, 0)

        f.write(patternArray_4k)
        remaining_blocks = remaining_blocks - 1

    f.close()
#
def read_and_verify_data_pattern(lbn_count, verify_type):
    result = OK
    remaining_blocks = lbn_count
    data_size = LBN_SIZE

    f = open("/dev/nvme0n1", "rb")

    while remaining_blocks > 0:
        # set position in file
        f.seek((lbn_count - remaining_blocks) * LBN_SIZE, 0)

        # choose pattern to verify
        if verify_type == "write":
            verify_pattern = bytearray(WRITE_4k_PATTERN)
        else:
            verify_pattern = bytearray(TRIM_4K_PATTERN)

        data = f.read(data_size)
        if data != verify_pattern:
            print("remaining blocks: {}".format(remaining_blocks))
            print("actually was readed: [{}]".format(data[0]))
            print("verify pattern: [{}]".format(verify_pattern[0]))
            print("Format Test: FAILED. Files are not equal.")
            result = FAIL
            break

        remaining_blocks = remaining_blocks - 1

    f.close()
    return result

def format_namespace():
    str1 = "sudo nvme format /dev/nvme0n1"
    out1, err1, rc = subprocess_send_command(str1)
    console_out(out1, err1)

def recreate_namespace():
    str1 = "sudo nvme delete-ns /dev/nvme0 -n 1"
    out1, err1, rc = subprocess_send_command(str1)
    console_out(out1, err1)

    drive_size = get_nvme_drive_size_in_lbn()
    str1 = "sudo nvme create-ns /dev/nvme0 -s {} -c {} -f 0".format(drive_size, drive_size)
    out1, err1, rc = subprocess_send_command(str1)
    console_out(out1, err1)

    str1 = "sudo nvme attach-ns /dev/nvme0 -c0 -n1"
    out1, err1, rc = subprocess_send_command(str1)
    console_out(out1, err1)

    str1 = "sudo nvme ns-rescan /dev/nvme0"
    out1, err1, rc = subprocess_send_command(str1)
    console_out(out1, err1)

def run_device_format_test(action_type):
    result = OK

    try:
        print("write pattern - \t{}".format(time.strftime("%H:%M:%S")))
        write_data_pattern(LBN_TO_VERIFY)

        print("read pattern - \t\t{}".format(time.strftime("%H:%M:%S")))
        result = read_and_verify_data_pattern(LBN_TO_VERIFY, "write")
        if result == OK:
            if action_type == "format":
                print("format namespace - \t\t{}".format(time.strftime("%H:%M:%S")))
                format_namespace()
            elif action_type == "delete":
                print("recreate namespace - \t\t{}".format(time.strftime("%H:%M:%S")))
                recreate_namespace()
            else:
                print("Wrong --action-type parameter.")
                result = FAIL
            time.sleep(2*SLEEP_TIME)

            if result == OK:
                print("read format pattern - \t{}".format(time.strftime("%H:%M:%S")))
                result = read_and_verify_data_pattern(LBN_TO_VERIFY, "format")

        print("test finished - \t{}".format(time.strftime("%H:%M:%S")))

        time.sleep(SLEEP_TIME)

    except Exception as e:
        print(e)
        raise

    return result

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


class TestFormat():

    @pytest.mark.parametrize("action", ["format", "delete"])
    def test_format(self, action):
        print ("\n")
        print("Execute...{}".format(action))
        subprocess.run(["nvme version"], check=False, shell=True)
        load_nvme_driver()

        print("List Controllers before IO tests")
        send_command_with_output_logging(_CMD_NVME_LIST)
        send_command_with_output_logging(_CMD_LS_NVME_DEVICES)

        result = run_device_format_test(action)

        if result == OK:
            print("Format Test: PASSED\n")
        else:
            pytest.fail("Format Test: FAILED\n")
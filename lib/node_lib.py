import os
import subprocess
import time
from waiters import timeout_decorator

def load_nvme_driver():
    ''' remove dnvme as it might be loaded and block loading nvme driver '''
#    print ("load driver")
    subprocess_send_cmd('sudo rmmod dnvme')
    timeout = 2
    out, err, rc = subprocess_send_cmd('sudo modprobe nvme && sleep {}'.format(timeout))
    assert rc == 0, "{}".format(err)
#    if rc:
#        raise Exception(err.decode('utf-8'))


def remove_nvme_driver():
#    print ("remove driver")
    timeout = 2
    out, err, rc = subprocess_send_cmd('sudo modprobe -r nvme && sleep {}'.format(timeout))
    assert rc == 0, "{}".format(err)
#    if rc:
#        raise Exception(err.decode('utf-8'))


def subprocess_send_cmd(cmd, timeout=None):
    print ("Executing command {}".format(cmd))
    ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#    out, err = ps.communicate()
    
    try:
        out, err = ps.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        ps.kill()
        out, err = ps.communicate()
        rc = ps.returncode
        err = "Timeout during command execution"
        return out, err, rc
    
    rc = ps.returncode
    
#    out = out.decode('utf-8').rstrip('\n')
#    err = err.decode('utf-8').rstrip('\n')
    
    '''
    print ("out: {}".format(out))
    print ("err: {}".format(err))
    print ("rc: {}".format(rc, type(rc)))
	'''
    return out, err, rc	

def get_pci_address():
    '''
        Finds a Marvell device and returns its PCI address in format: DDDD:BB:DD.F.
        That is Domain:Bus:Device.Function
    '''
    address = ''
    cmd = 'lspci | grep Marvell'
    out, err, rc = subprocess_send_cmd (cmd)
    out_string = out.decode('utf-8').rstrip('\n')

    if not out_string:
        return None

    address = out_string.split()[0]
    address = '0000:' + address
    print('Found a Marvell device, PCI address: {0}'.format(address))

    return address

def get_pci_bridge_address(pci_address):
    '''
        Returns PCI bridge address
    '''
    path = '/sys/bus/pci/devices/{0}'.format(pci_address)
    if not os.path.exists(path):
        return None

    '''
        For example the path to our device in sysfs looks like /sys/bus/pci/devices/0000:01:00.0
        Where 0000:01:00.0 is PCI address. After execute readlink() we will get path
        ../../../devices/pci0000:00/0000:00:01.0/0000:01:00.0
        where 0000:00:01.0 - PCI bridge address
    '''
    path = os.readlink(path)
    path = os.path.dirname(path)
    bridge_address = os.path.basename(path)
    print("PCI bridge address: {0}".format(bridge_address))

    return bridge_address

@timeout_decorator(10)
def wait_controller_available(fun_id, stop_event=None):
    while not stop_event.is_set():
        if is_nvme_controller_available(fun_id):
            break

@timeout_decorator(10)
def is_nvme_controller_available(fun_id, stop_event=None):
    while True:
        out, err, rc = subprocess_send_cmd("ls /dev/nvme0n*")
        if out != b'':
            break

    time.sleep(1)

    out, err, rc = subprocess_send_cmd("sudo nvme id-ctrl /dev/nvme{} -o json".format(fun_id))
    if rc == 0:
        return True
    else:
        return False

def conventional_reset():
    print ("\n")
    pci_address = get_pci_address()
    assert pci_address, "Device was not detected!"

    bridge_address = get_pci_bridge_address(pci_address)
    assert bridge_address, "PCI bridge was not detected!"

    # Prepare for hot reset.
    remove_nvme_driver()
    time.sleep(1)
    subprocess_send_cmd("echo 1 | sudo /usr/bin/tee /sys/bus/pci/devices/" + pci_address + "/remove")

    # Issue hot reset.
    # Read the current value of the register BRIDGE_CONTROL
    out, err, rc = subprocess_send_cmd("sudo setpci -s {} BRIDGE_CONTROL".format(bridge_address))
    assert err == b'', "Failed with error({})".format(err)
		
    # Convert BRIDGE CONTROL register to hex
    bc = out.decode('utf-8').rstrip('\n')
#    bc = out
    bridge_control_register = int(bc, 16)

    # Set the Secondary Bus Reset bit
    bridge_control_register = '{:04x}'.format(bridge_control_register | 0x40)
    out, err, rc = subprocess_send_cmd("sudo setpci -s {} BRIDGE_CONTROL={}".format(bridge_address, bridge_control_register))
    assert err == b'', "Failed with error({})".format(err)
    time.sleep(0.1)

    # Clear the Secondary Bus Reset bit by resetting the BRIDGE_CONTROL register to its original state
    out, err, rc = subprocess_send_cmd("sudo setpci -s {} BRIDGE_CONTROL={}".format(bridge_address, bc))
    assert err == b'', "Failed with error({})".format(err)

    '''
        Search for the PCIe device and check the NVMe controller to understand
        that the device is accessible after conventional reset.
    '''
    max_retries = 5
    num_retry = 0
    is_device_found = False

    while is_device_found is not True and num_retry < max_retries:
        # Rescan the PCI bus
        out, err, rc = subprocess_send_cmd("echo 1 | sudo /usr/bin/tee /sys/bus/pci/devices/{}/rescan".format(bridge_address))
        assert err == b'', "Failed with error({})".format(err)
        time.sleep(1)
        # Verify that PCI address is available
        if get_pci_address():
            load_nvme_driver()
            # Check controller /dev/nvme0
            is_device_found = is_nvme_controller_available(0)
            if is_device_found:
                print("Found Marvell device!")
            else:
                print("NVMe controller not found, retry {0}/{1} times".format(num_retry, max_retries))
                time.sleep(5)
                num_retry += 1
        else:
            print("Marvell device not found, retry {0}/{1} times".format(num_retry, max_retries))
            time.sleep(5)
            num_retry += 1

    return is_device_found
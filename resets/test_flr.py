import subprocess
import os
import time
import pytest
import sys
sys.path.append('../lib')
import node_lib

_PF_ID = 0
_NUM_VFS = 4



def _create_vfs(device_pci_address, numvfs):
    """
        Creates a specified number of PCIe Virtual Functions
    """
    print ('Create {} PCIe VFs'.format(numvfs))
    cmd = "/bin/echo {0} | sudo /usr/bin/tee /sys/bus/pci/devices/{1}/sriov_numvfs".format(numvfs, device_pci_address)
    node_lib.subprocess_send_cmd(cmd)	

    device = "/dev/nvme0"
    cmd = "nvme ns-rescan {}".format(device)
#    cmd = "/bin/echo 1 | sudo /usr/bin/tee /sys/class/nvme/{0}/rescan_controller".format(os.path.basename(device))
    out, err, rc = node_lib.subprocess_send_cmd(cmd)

    time.sleep(1)

    cmd = "/bin/cat /sys/bus/pci/devices/{0}/sriov_numvfs".format(device_pci_address)
    out, err, rc = node_lib.subprocess_send_cmd(cmd)
    out = out.decode('utf-8').rstrip('\n')
    print (out)

    assert int(out[0]) == numvfs, "Failed to create VFs"

    return range(1, numvfs + 1)
#







def _execute_functional_level_reset(device_pci_address, fun_id):
    """
         Executes Functional Level Reset
         The PCI address has the format DDDD:BB:DD.F, where "F" is the PCI Function Identifier,
         which is passed to this function in the fun_id parameter.
    """
    pci_address_function_to_reset = device_pci_address[:-1] + str(fun_id)

    path = '/sys/bus/pci/devices/{0}'.format(pci_address_function_to_reset)
    assert os.path.exists(path), "Path to a function not exist"

    print('Execute Function Level Reset, PCI function address: {0}'.format(pci_address_function_to_reset))
    cmd = "/bin/echo 1 | sudo /usr/bin/tee /sys/bus/pci/devices/{0}/reset".format(pci_address_function_to_reset)
    node_lib.subprocess_send_cmd(cmd)

    if fun_id is _PF_ID:
        ''' During the execution of FLR a Physical Function all Virtual Functions were disabled in our firmware, but Linux does not know anything about it.
            Simply remove the device from the system and return it to perform initialization.
            Some delays before and after this procedure have been added to make sure that the re-initialization has been completed and we can go further.
        '''
        time.sleep(2)

        node_lib.remove_nvme_driver()

        node_lib.subprocess_send_cmd("/bin/echo 1 | sudo /usr/bin/tee /sys/bus/pci/devices/{}/remove".format(pci_address_function_to_reset))

        # Rescan PCI bus to return back our device after removing
        node_lib.subprocess_send_cmd("/bin/echo 1 | sudo /usr/bin/tee /sys/bus/pci/rescan")
        time.sleep(2)

        node_lib.load_nvme_driver()

    # Check if the NVMe controller is available after resetting the function

    node_lib.wait_controller_available(fun_id)
















class TestFlr():

    def test_flr(self):

        pci_address = node_lib.get_pci_address()
        vf_range = _create_vfs(pci_address, _NUM_VFS)

        # Execute reset for each Virtual Function
        for vf_id in vf_range:
            _execute_functional_level_reset(pci_address, vf_id)
			
        # Restore Default Configuration
#        print ("RESTORE DEFAULT")
        cmd = "/bin/echo 0 | sudo /usr/bin/tee /sys/bus/pci/devices/{0}/sriov_numvfs".format(pci_address)
        node_lib.subprocess_send_cmd(cmd)
		
        # Reset physical function
        _execute_functional_level_reset(pci_address, _PF_ID)



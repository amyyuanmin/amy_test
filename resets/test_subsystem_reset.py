import subprocess
import os
import time
import pytest
import sys
sys.path.append('../lib')
import node_lib

class TestSubsystemReset():

    def test_subsystem_reset(self):

        node_lib.load_nvme_driver()

        ''' make sure we are able to write some data '''
        device = "/dev/nvme0"
        start_block = 0
        block_count = 1
        data_file = "/dev/urandom"
        data_size = 1024
        cmd = "sudo nvme write {0} --start-block {1} --block-count {2} --data={3} --data-size={4}".format(device, start_block, block_count, data_file, data_size)
#        print (cmd)
        out, err, rc = node_lib.subprocess_send_cmd(cmd)
        assert rc == 0, "writing failed"


        ''' issue subsystem reset and check that there are no errors '''
        cmd = "sudo nvme subsystem-reset {0}".format(device)
#        print (cmd)
        out, err, rc = node_lib.subprocess_send_cmd(cmd)
        assert rc == 0, "Subsystem reset failed"

        cmd = "sudo nvme write {0} --start-block {1} --block-count {2} --data={3} --data-size={4}".format(device, start_block, block_count, data_file, data_size)
        out, err, rc = node_lib.subprocess_send_cmd(cmd)
        assert rc == 0, 'writing failed. Check subsystem reset logic.'

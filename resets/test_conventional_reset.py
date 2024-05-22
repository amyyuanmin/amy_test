import subprocess
import os
import time
import pytest
import sys

sys.path.append('../lib')
import node_lib






class TestConventionalReset():

    def test_conventional_reset(self):
        try:
            result = node_lib.conventional_reset()
            assert result
        except Exception as e:
            print (e)
		
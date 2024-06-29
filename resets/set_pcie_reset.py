#!/usr/bin/python
import re
import subprocess
import time


def pcie_reset_test():
    for i in range(0,1000):
        os.system("./pcie_hot_reset.sh 03:00.0)
    



if __name__ == "__main__":
    pcie_reset_test()
#!/usr/bin/python
import re
import subprocess
import time


def flr_test():

    pci_bdf = subprocess.getoutput("lspci | grep Non-Volatile")
    bdf = pci_bdf[0:7]

    Cap = subprocess.getoutput("lspci -vs %s" %bdf)
    dev_cap = re.findall(r"(\d+)] Express", Cap)
    print(dev_cap[0])
    dcap = int(dev_cap[0])+8
    dev_ctrl = subprocess.getoutput("setpci -s %s %d.w" % (bdf,dcap))
    print("setpci -s %s %d.w" % (bdf,dcap))
    dev_ctrl = int(dev_ctrl, 16)
    print(dev_ctrl)
    dev_ctrl = dev_ctrl |0x8000
    print(dev_ctrl)


    #set ASPM to 0
    aspm_ctrl = int(dev_cap[0])+10
    print(aspm_ctrl)
    aspm = subprocess.getoutput("setpci -s %s %d.w" % (bdf,aspm_ctrl))
    print("setpci -s %s %d.w" % (bdf,aspm_ctrl))
    aspm = int(aspm,16)
    print(aspm)
    aspm = aspm & 0xfffc
    print(aspm)
    subprocess.call("setpci -s %s %d.L=%s" %(bdf, aspm_ctrl, hex(aspm)), shell=True)
    print("setpci -s %s %d.L=%s" %(bdf, aspm_ctrl, hex(aspm)))
    #flr
    bdf1="0000:0e:00.0"
    subprocess.call('echo "ldbe 5236" > "/sys/bus/pci/devices/%s/driver/remove_id" 2 > /dev/null' % bdf1, shell=True)
    subprocess.call('echo "%s" > "/sys/bus/pci/devices/%s/driver/unbind" 2> /dev/null' %(bdf1, bdf1), shell=True)

    print('echo "ldbe 5236" > "/sys/bus/pci/devices/%s/driver/remove_id" 2 > /dev/null' % bdf1)
    print('echo "%s" > "/sys/bus/pci/devices/%s/driver/unbind" 2> /dev/null' %(bdf1, bdf1))

    subprocess.call("setpci -s %s %d.L=%s" %(bdf, dcap, hex(dev_ctrl)), shell=True)
    print("setpci -s %s %d.L=%s" %(bdf, dcap, hex(dev_ctrl)))
    time.sleep(0.1)
    subprocess.call('echo "1" > /sys/bus/pci/devices/0000:%s/remove' % bdf, shell=True)
    time.sleep(1)
    subprocess.call('echo "1" > /sys/bus/pci/rescan', shell=True)




if __name__ == "__main__":
    flr_test()
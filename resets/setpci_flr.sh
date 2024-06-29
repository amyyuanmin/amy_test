#!/bin/bash

dev=$1
echo $dev
if [ "$2" ];then filename=$2
else filename=flr_test.log
fi
echo $filename
if [ -z "$dev" ]; then
    echo "Error: no device specified"
    exit 1
fi
 
if [ ! -e "/sys/bus/pci/devices/$dev" ]; then
    dev1=$(echo $dev | cut -d':' -f1)
    dev2=$(echo $dev | cut -d':' -f2)
    echo $dev1
    echo $dev2
    dev="0000:$dev"

fi
 
if [ ! -e "/sys/bus/pci/devices/$dev" ]; then
    echo "Error: device $dev not found"
    exit 1
fi

echo $dev

pciec=$(sudo setpci -s $dev CAP_EXP+8.W)
echo $pciec
lcn=$(printf "%08x" $((0x$pciec | 0x8000)))  #A write of ‘1’ initiates Function Level Reset to the Function 
echo $lcn
sudo setpci -s $dev CAP_EXP+8.W=$lcn
echo "have send FLR"


sudo echo 1 >/sys/bus/pci/devices/0000\:$dev1\:$dev2/remove 
sudo echo 1 >/sys/bus/pci/rescan
echo "have finished rescan"
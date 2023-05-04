#!/bin/bash

dev=$1
speed=$2
if [ "$3" ];then filename=$3
else filename=link_speed.log
fi
if [ -z "$dev" ]; then
    echo "Error: no device specified"
    exit 1
fi
 
if [ ! -e "/sys/bus/pci/devices/$dev" ]; then
    dev="0000:$dev"
fi
 
if [ ! -e "/sys/bus/pci/devices/$dev" ]; then
    echo "Error: device $dev not found"
    exit 1
fi
 
pciec=$(setpci -s $dev CAP_EXP+02.W)
pt=$(((0x$pciec & 0xF0) >> 4))
 
port=$(basename $(dirname $(readlink "/sys/bus/pci/devices/$dev")))
 
if (($pt == 0)) || (($pt == 1)) || (($pt == 5)); then
    dev=$port
fi
 
lc=$(setpci -s $dev CAP_EXP+0c.L)
ls=$(setpci -s $dev CAP_EXP+12.W)
 
max_speed=$((0x$lc & 0xF))
 
echo "Link capabilities:" $lc  | tee -a $filename
echo "Max link speed:" $max_speed  | tee -a $filename
echo "Link status:" $ls  | tee -a $filename
echo "~~~~~~~~Current link speed:" $((0x$ls & 0xF))  | tee -a $filename
 
if [ -z "$speed" ]; then
    speed=$max_speed
fi
 
if (($speed > $max_speed)); then
    speed=$max_speed
fi
 
echo "Configuring $dev..."  | tee -a $filename
 
lc2=$(setpci -s $dev CAP_EXP+30.L)
 
echo "Original link control 2:" $lc2  | tee -a $filename
echo "Original link target speed:" $((0x$lc2 & 0xF)) | tee -a $filename
 
lc2n=$(printf "%08x" $(((0x$lc2 & 0xFFFFFFF0) | $speed)))
 
echo "---------New target link speed---------:" $speed | tee -a $filename
echo "New link control 2:" $lc2n | tee -a $filename
 
setpci -s $dev CAP_EXP+30.L=$lc2n
 
echo "Triggering link retraining..." | tee -a $filename
 
lc=$(setpci -s $dev CAP_EXP+10.L)
 
echo "Original link control:" $lc | tee -a $filename
 
lcn=$(printf "%08x" $((0x$lc | 0x20)))
 
echo "New link control:" $lcn | tee -a $filename
 
setpci -s $dev CAP_EXP+10.L=$lcn | tee -a $filename
 
sleep 0.1
 
ls=$(setpci -s $dev CAP_EXP+12.W)
 
echo "Link status:" $ls | tee -a $filename
echo "---------Current link speed---------:" $((0x$ls & 0xF)) | tee -a $filename

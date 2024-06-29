Based on Linux kernel 4.15(Ubuntu 18.04)

How to re-generate nvme driver:
1. Replace core.c nvme.h Makefile under linux-4.15/drivers/nvme/host/
2. Compile by make
3. Re-load nvme driver:
rmmod nvme
rmmod nvme-core
insmod nvme-core.ko
insmod nvme.ko


Test command: nvme admin-passthru /dev/nvme0n1 -o 0xC0
check result via dmesg log.
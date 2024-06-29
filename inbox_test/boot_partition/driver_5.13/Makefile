DIST ?= $(shell uname -r)
KDIR:=/lib/modules/$(DIST)/build/
CDIR:=/usr/src/$(DIST)-generic/debian/scripts/
SOURCE:=$(shell pwd)

# SPDX-License-Identifier: GPL-2.0

ccflags-y                               += -I$(src)

obj-$(CONFIG_NVME_CORE)			+= nvme-core.o
obj-$(CONFIG_BLK_DEV_NVME)		+= nvme.o

nvme-core-y				:= core.o ioctl.o
nvme-core-$(CONFIG_TRACING)             += trace.o
nvme-core-$(CONFIG_NVME_MULTIPATH)	+= multipath.o
nvme-core-$(CONFIG_NVM)			+= lightnvm.o
nvme-core-$(CONFIG_BLK_DEV_ZONED)       += zns.o
nvme-core-$(CONFIG_FAULT_INJECTION_DEBUG_FS)     += fault_inject.o
nvme-core-$(CONFIG_NVME_HWMON)          += hwmon.o

nvme-y					+= pci.o

#---------------------------------------------

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) -Wall clean
	-rm -f doxygen.log
	-rm -rf $(SRCDIR)



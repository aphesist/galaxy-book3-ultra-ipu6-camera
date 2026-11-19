# PSYS-only build of intel/ipu6-drivers for kernels >= 6.10, where ISYS is in-tree.
KERNELRELEASE ?= $(shell uname -r)
KERNEL_SRC ?= /lib/modules/$(KERNELRELEASE)/build
export CONFIG_VIDEO_INTEL_IPU6 = m
export EXTERNAL_BUILD = 1
obj-y += drivers/media/pci/intel/ipu6/psys/
subdir-ccflags-y += -I$(src)/include/ -DCONFIG_VIDEO_V4L2_SUBDEV_API
all:
	$(MAKE) -C $(KERNEL_SRC) M=$(CURDIR) modules
clean:
	$(MAKE) -C $(KERNEL_SRC) M=$(CURDIR) clean

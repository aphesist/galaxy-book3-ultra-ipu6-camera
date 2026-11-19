#!/usr/bin/env python3
"""Flip the OV02C10 image 180 degrees in Intel's HAL sensor config.

The sensor is mounted upside down on the Galaxy Book3 Ultra. libcamera's own
pipelines read the driver's rotation=180 and enable the sensor flips; Intel's
HAL ignores it, so the flips are set as media-controller controls instead.
The patched ov02c10 driver keeps the Bayer order (SGRBG10) when flipped.

Usage: ov02c10-flip.py <path to sensors/ov02c10-uf.xml>   (idempotent)
"""
import re
import sys

path = sys.argv[1]
s = open(path).read()
if 'ctrlId="V4L2_CID_VFLIP"' in s:
    print("already flipped:", path)
    sys.exit(0)

controls = (
    '<control name="ov02c10 $I2CBUS" ctrlId="V4L2_CID_VFLIP" value="1" ctrlName="set vflip"/>\n'
    '{i}<control name="ov02c10 $I2CBUS" ctrlId="V4L2_CID_HFLIP" value="1" ctrlName="set hflip"/>\n\n'
    '{i}'
)


def add(block):
    m = re.search(r'\n([ \t]*)<videonode ', block.group(0))
    if not m:
        return block.group(0)
    indent = m.group(1)
    b = block.group(0)
    pos = m.start() + 1 + len(indent)
    return b[:pos] + controls.format(i=indent) + b[pos:]


s, n = re.subn(r'<MediaCtlConfig\b.*?</MediaCtlConfig>', add, s, flags=re.S)
if n == 0:
    sys.exit("no MediaCtlConfig blocks found in " + path)
open(path, 'w').write(s)
print(f"flipped {n} MediaCtlConfig blocks:", path)

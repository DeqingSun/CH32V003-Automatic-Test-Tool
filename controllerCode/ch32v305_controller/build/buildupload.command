#!/usr/bin/env bash
./build.sh compile
../../../autoTestCode/lib/toolBinary/minichlink_mac -C linke -l 894E8F060E2C -w build_out/ch32v305_controller.ino.bin 0x08000000

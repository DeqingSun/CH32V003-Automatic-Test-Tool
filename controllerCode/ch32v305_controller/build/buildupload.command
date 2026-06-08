#!/usr/bin/env bash
./build.sh compile
../../../autoTestCode/toolBinary/minichlink -C linke -l 894E8F060E2C -w build_out/ch32v305_controller.ino.bin 0x08000000

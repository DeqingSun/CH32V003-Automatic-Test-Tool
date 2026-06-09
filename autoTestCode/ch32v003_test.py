# test CH32V003

from ch32v003_test_target import Ch32V003_test_target

test_ch32v003_test_target = Ch32V003_test_target()
ret = test_ch32v003_test_target.initialize()
if (ret == True):
    print("Test target initialized")
else:
    print("Test target initialization failed")
    exit(1)

ret = test_ch32v003_test_target.flashFirmware("/Users/deqinguser/Documents/GitHub/CH32V003-Automatic-Test-Tool/autoTestCode/sampleArtifacts/examples/blink/blink.bin")
if (ret == True):
    print("Firmware flashed")
else:
    print("Firmware flashing failed")
    exit(1)
#connect PD0(pin8) to LED
test_ch32v003_test_target.connectPin("PD0", "304_PA7")
test_ch32v003_test_target.connectPin("X6", "304_PA7")

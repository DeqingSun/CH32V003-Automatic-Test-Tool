# test CH32V003

import time, os
import serial
import serial.tools.list_ports
import subprocess
from ch32V305CCT6_test_tool import Ch32V305CCT6_test_tool

class TestCh32V003:
    def __init__(self):
        self.test_tool = Ch32V305CCT6_test_tool()

    def initialize(self):
        self.test_tool.connect()
        ret = self.test_tool.initailize(0.5)
        if (ret == True):
            return True
        else:
            return False

    def resetMatrix(self):
        ret = self.test_tool.initailize(0.5)
        if (ret == True):
            return True
        else:
            return False

    def flashFirmware(self, firmware_path, wch_linke_serial_number = None):
        #check if the firmware file exists
        if (not os.path.exists(firmware_path)):
            print("Firmware file not found: "+firmware_path)
            return False
        #check if the minichlink is ready in toolBinary folder
        current_script_directory = os.path.dirname(os.path.abspath(__file__))
        tool_binary_directory = os.path.join(current_script_directory, "toolBinary")
        if (not os.path.exists(os.path.join(tool_binary_directory, "minichlink"))):
            print("Minichlink not found in toolBinary folder")
            return False

        #for ch32v003, the SWIO is on PD1, pin 18 on TSSOP20 package
        #we can route the SWIO to on board WCH-LINKE SWDIO via any input gpio on CH32V305
        self.test_tool.connect_pins(self.test_tool.SSOP20_PIN18_MAP, self.test_tool.Y_305_PA7, 0.5)
        self.test_tool.connect_pins(self.test_tool.WCH_LINKE_SWDIO, self.test_tool.Y_305_PA7, 0.5)

        #use the minichlink to flash the firmware
        #sample command: ./toolBinary/minichlink -C linke -l 2C868F06B189
        command_minichlink = f"./toolBinary/minichlink -C linke"
        if (wch_linke_serial_number is not None):
            command_minichlink = command_minichlink + f" -l {wch_linke_serial_number}"
        #run command and see if there is "Detected CH32V003" in the output
        result = subprocess.run(command_minichlink, shell=True, capture_output=True, text=True)
        if not (("Detected CH32V003" in result.stdout) or ("Detected CH32V003" in result.stderr)):
            print("CH32V003 target not found")
            return False

        #flash the firmware
        command_flash = command_minichlink + f" -w {firmware_path} 0x08000000"
        result = subprocess.run(command_flash, shell=True, capture_output=True, text=True)
        if not ("Image written" in result.stdout):
            print("Firmware flashing failed")
            return False
        
        self.resetMatrix()
        return True

test_ch32v003 = TestCh32V003()
test_ch32v003.initialize()
test_ch32v003.flashFirmware("/Users/deqinguser/Documents/GitHub/CH32V003-Automatic-Test-Tool/autoTestCode/sampleArtifacts/examples/blink/blink.bin")
#connect PD0(pin8) to LED
test_ch32v003.test_tool.connect_pins(test_ch32v003.test_tool.SSOP20_PIN8_MAP, test_ch32v003.test_tool.Y_305_PA7, 0.5)
test_ch32v003.test_tool.connect_pins(test_ch32v003.test_tool.PIN_X6, test_ch32v003.test_tool.Y_305_PA7, 0.5)

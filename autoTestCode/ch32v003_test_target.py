import os
import subprocess

from ch32V305CCT6_test_tool import Ch32V305CCT6_test_tool


class Ch32V003_test_target:
    def __init__(self):
        self.test_tool = Ch32V305CCT6_test_tool()
        self.map_dict = {
            "PD4": self.test_tool.SSOP20_PIN1_MAP,
            "PD5": self.test_tool.SSOP20_PIN2_MAP,
            "PD6": self.test_tool.SSOP20_PIN3_MAP,
            "PD7": self.test_tool.SSOP20_PIN4_MAP,
            "PA1": self.test_tool.SSOP20_PIN5_MAP,
            "PA2": self.test_tool.SSOP20_PIN6_MAP,
            "VSS": self.test_tool.SSOP20_PIN7_MAP,
            "PD0": self.test_tool.SSOP20_PIN8_MAP,
            "VDD": self.test_tool.SSOP20_PIN9_MAP,
            "PC0": self.test_tool.SSOP20_PIN10_MAP,
            "PC1": self.test_tool.SSOP20_PIN11_MAP,
            "PC2": self.test_tool.SSOP20_PIN12_MAP,
            "PC3": self.test_tool.SSOP20_PIN13_MAP,
            "PC4": self.test_tool.SSOP20_PIN14_MAP,
            "PC5": self.test_tool.SSOP20_PIN15_MAP,
            "PC6": self.test_tool.SSOP20_PIN16_MAP,
            "PC7": self.test_tool.SSOP20_PIN17_MAP,
            "PD1": self.test_tool.SSOP20_PIN18_MAP,
            "PD2": self.test_tool.SSOP20_PIN19_MAP,
            "PD3": self.test_tool.SSOP20_PIN20_MAP,
            "X0": self.test_tool.PIN_X0,
            "X1": self.test_tool.PIN_X1,
            "X2": self.test_tool.PIN_X2,
            "X3": self.test_tool.PIN_X3,
            "X4": self.test_tool.PIN_X4,
            "X5": self.test_tool.PIN_X5,
            "X6": self.test_tool.PIN_X6,
            "304_PA0": self.test_tool.Y_305_PA0,
            "304_PA1": self.test_tool.Y_305_PA1,
            "304_PA2": self.test_tool.Y_305_PA2,
            "304_PA3": self.test_tool.Y_305_PA3,
            "304_PA4": self.test_tool.Y_305_PA4,
            "304_PA5": self.test_tool.Y_305_PA5,
            "304_PA6": self.test_tool.Y_305_PA6,
            "304_PA7": self.test_tool.Y_305_PA7,
        }

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

    def connectPin(self, pin_name, pin_305_gpio_name):
        if (pin_name not in self.map_dict):
            print("Pin not found: "+pin_name)
            return False
        if (pin_305_gpio_name not in self.map_dict):
            print("Pin not found: "+pin_305_gpio_name)
            return False
        self.test_tool.connect_pins(self.map_dict[pin_name], self.map_dict[pin_305_gpio_name], 0.5)
        return True

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
            # print(result.stdout)
            # print(result.stderr)
            return False

        #flash the firmware
        command_flash = command_minichlink + f" -w {firmware_path} 0x08000000"
        result = subprocess.run(command_flash, shell=True, capture_output=True, text=True)
        if not ("Image written" in result.stdout):
            print("Firmware flashing failed")
            return False

        self.resetMatrix()
        return True

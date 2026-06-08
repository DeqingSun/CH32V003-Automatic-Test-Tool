import time
import serial
import serial.tools.list_ports

class Ch32V305CCT6_test_tool:
    def __init__(self):
        self.SSOP20_PIN1_MAP  = 27
        self.SSOP20_PIN2_MAP  = 26
        self.SSOP20_PIN3_MAP  = 25
        self.SSOP20_PIN4_MAP  = 24
        self.SSOP20_PIN5_MAP  = 23
        self.SSOP20_PIN6_MAP  = 22
        self.SSOP20_PIN7_MAP  = 31
        self.SSOP20_PIN8_MAP  = 30
        self.SSOP20_PIN9_MAP  = 12
        self.SSOP20_PIN10_MAP = 13
        self.SSOP20_PIN11_MAP = 15
        self.SSOP20_PIN12_MAP = 14
        self.SSOP20_PIN13_MAP = 29
        self.SSOP20_PIN14_MAP = 19
        self.SSOP20_PIN15_MAP = 28
        self.SSOP20_PIN16_MAP = 18
        self.SSOP20_PIN17_MAP = 21
        self.SSOP20_PIN18_MAP = 17
        self.SSOP20_PIN19_MAP = 20
        self.SSOP20_PIN20_MAP = 16

        self.WCH_LINKE_SWCLK =  9
        self.WCH_LINKE_SWDIO =  8
        self.WCH_LINKE_TX    = 11
        self.WCH_LINKE_RX    = 10
        self.WCH_LINKE_RST   =  7

        self.PIN_X0 = 0
        self.PIN_X1 = 1
        self.PIN_X2 = 2
        self.PIN_X3 = 3
        self.PIN_X4 = 4
        self.PIN_X5 = 5
        self.PIN_X6 = 6

        self.Y_305_PA0 = 0
        self.Y_305_PA1 = 1
        self.Y_305_PA2 = 2
        self.Y_305_PA3 = 3
        self.Y_305_PA4 = 4
        self.Y_305_PA5 = 5
        self.Y_305_PA6 = 6
        self.Y_305_PA7 = 7

        self.serial_port = None
        self.serial_buffer = ""
        self.print_serial_input = False
        

    def connect(self):
        v305_port = None
        for port in serial.tools.list_ports.comports():
            if ((port.serial_number == "CH32V30x")):
                v305_port = port
                break
        if (v305_port == None):
            print("CH32V30x test tool not found")
            return False
        try:
            self.serial_port = serial.Serial(v305_port.device, 115200, timeout=0)
        except Exception as e:
            print("CH32V30x test tool open failed on "+v305_port.device+" with error: "+type(e).__name__)
            return False
        if (self.serial_port == None):
            print("CH32V30x test tool open failed on "+v305_port.device)
            return False
        return True
        
    def disconnect(self):
        if (self.serial_port == None):
            return
        self.serial_port.close()
        self.serial_port = None

    def check_input(self):
        return_list = []
        if (self.serial_port == None):
            return return_list
        if (self.serial_port.in_waiting == 0):
            return return_list
        input_bytes = self.serial_port.read(self.serial_port.in_waiting)
        input_string = input_bytes.decode('ascii', errors='ignore')
        while ( (pos_newline := input_string.find('\n')) >=0 ):
            part_before_newline = input_string[0:pos_newline]
            part_after_newline = input_string[pos_newline+1:]
            self.serial_buffer = self.serial_buffer+part_before_newline
            if (len(self.serial_buffer)>0):
                if (self.print_serial_input):
                    print(self.serial_buffer)
                if (self.serial_buffer.startswith("U:")):
                    self.uart0_buffer = self.uart0_buffer + self.serial_buffer[2:].strip("\n\r")
                return_list.append(self.serial_buffer.strip())
            self.serial_buffer = ""
            input_string = part_after_newline
        self.serial_buffer = self.serial_buffer+input_string
        return return_list
    
    def write_string_wait_for_response(self, string, string_to_wait,wait_for_input_time):
        if (self.serial_port == None):
            return ""
        if (len(string)>0):
            self.serial_port.write(string.encode('ascii'))
        if (wait_for_input_time == 0):
            #assume the command got processed successfully
            return ""
        else:
            #wait for the input
            if (len(string)>0):
                self.serial_port.flush()
            start_time = time.monotonic()
            while (time.monotonic() - start_time < wait_for_input_time):
                time.sleep(0.001)
                response = self.check_input()
                if (len(response) > 0):
                    for line in response:
                        if string_to_wait in line:
                            return line
            return ""
    
    def initailize(self, wait_for_input_time=0):
        command = "I\n"
        write_response = self.write_string_wait_for_response(command, "I:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            return (len(write_response)>0)

    def connect_pins(self, pin_X, pin_305_GPIO_pin_Y, wait_for_input_time=0):
        command = f"C{pin_X:02X}{pin_305_GPIO_pin_Y:X}\n"
        write_response = self.write_string_wait_for_response(command, "C:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            return (len(write_response)>0)
        
    def disconnect_pins(self, pin_X, pin_305_GPIO_pin_Y, wait_for_input_time=0):
        command = f"c{pin_X:02X}{pin_305_GPIO_pin_Y:X}\n"
        write_response = self.write_string_wait_for_response(command, "c:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            return (len(write_response)>0)
        
    def analog_read(self, pin, wait_for_input_time=1):
        command = f"A{pin:02d}\n"
        responseHeader = f"A{pin:02d}:"
        write_response = self.write_string_wait_for_response(command, responseHeader, wait_for_input_time)
        if (wait_for_input_time == 0):
            return None
        else:
            if (len(write_response)>0):
                try:
                    colon_pos = write_response.find(":")
                    return (int(write_response[colon_pos+1:]))
                except:
                    return None
            else:
                return None
            
    def analog_write(self, pin, value, wait_for_input_time=0):
        command = f"w{pin:02d}{value:02x}\n"
        write_response = self.write_string_wait_for_response(command, f"w{pin:02d}:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            if (len(write_response)==0):
                return False
            if ("not valid" in write_response):
                return False
            return True
    
    def digital_write(self, pin, value, wait_for_input_time=0):
        if (value == True):
            value = 1
        if (value == False):
            value = 0
        command = f"W{pin:02d}{value}\n"
        write_response = self.write_string_wait_for_response(command, f"W{pin:02d}:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            if (len(write_response)==0):
                return False
            if ("not valid" in write_response):
                return False
            return True
        
    def digital_read(self, pin, wait_for_input_time=1):
        command = f"R{pin:02d}\n"
        responseHeader = f"R{pin:02d}:"
        write_response = self.write_string_wait_for_response(command, responseHeader, wait_for_input_time)
        if (wait_for_input_time == 0):
            return None
        else:
            if (len(write_response)>0):
                try:
                    colon_pos = write_response.find(":")
                    return (int(write_response[colon_pos+1])>0)
                except:
                    return None
            else:
                return None
    
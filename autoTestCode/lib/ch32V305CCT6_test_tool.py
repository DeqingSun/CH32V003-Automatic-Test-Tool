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
        self.usb_location = None
        

    def connect(self, port=None):
        if port is None:
            v305_port = None
            for listed_port in serial.tools.list_ports.comports():
                if ((listed_port.serial_number == "CH32V30x")):
                    v305_port = listed_port
                    break
            if (v305_port == None):
                print("CH32V30x test tool not found")
                return False
            device = v305_port.device
            self.usb_location = v305_port.location
        else:
            device = port
            for listed_port in serial.tools.list_ports.comports():
                if (listed_port.device == port):
                    self.usb_location = listed_port.location
                    break
        try:
            self.serial_port = serial.Serial(device, 115200, timeout=0)
        except Exception as e:
            print("CH32V30x test tool open failed on "+device+" with error: "+type(e).__name__)
            return False
        if (self.serial_port == None):
            print("CH32V30x test tool open failed on "+device)
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
    
    def send_command_batch(self, commands, flush=True):
        if (self.serial_port == None):
            return False
        if (len(commands) == 0):
            return True
        payload = "\n".join(commands) + "\n"
        self.serial_port.write(payload.encode('ascii'))
        if (flush):
            self.serial_port.flush()
        return True

    def write_batch_wait_for_response(self, commands, string_to_wait, wait_for_input_time):
        if (self.serial_port == None):
            return ""
        if (len(commands) == 0):
            return ""
        payload = "\n".join(commands) + "\n"
        self.serial_port.write(payload.encode('ascii'))
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

    @staticmethod
    def digital_write_command(pin, value):
        if (value == True):
            value = 1
        if (value == False):
            value = 0
        return f"W{pin:01d}{value}"

    @staticmethod
    def build_digital_pulse_train(pin, pulse_count):
        commands = []
        for _ in range(pulse_count):
            commands.append(Ch32V305CCT6_test_tool.digital_write_command(pin, False))
            commands.append(Ch32V305CCT6_test_tool.digital_write_command(pin, True))
        return commands

    def initailize(self, wait_for_input_time=0):
        command = "I\n"
        write_response = self.write_string_wait_for_response(command, "I:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            return (len(write_response)>0)

    def save_matrix(self, wait_for_input_time=0):
        command = "S\n"
        write_response = self.write_string_wait_for_response(command, "S:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            return (len(write_response)>0)

    def restore_matrix(self, wait_for_input_time=0):
        command = "s\n"
        write_response = self.write_string_wait_for_response(command, "s:", wait_for_input_time)
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
        command = f"A{pin:01d}\n"
        responseHeader = f"A{pin:01d}:"
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
        command = f"w{pin:01d}{value:04x}\n"
        write_response = self.write_string_wait_for_response(command, f"w{pin:01d}:", wait_for_input_time)
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
        command = f"W{pin:01d}{value}\n"
        write_response = self.write_string_wait_for_response(command, f"W{pin:01d}:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            if (len(write_response)==0):
                return False
            if ("not valid" in write_response):
                return False
            return True
        
    def digital_read(self, pin, wait_for_input_time=1):
        """Read without changing pin mode (firmware `r`)."""
        command = f"r{pin:01d}\n"
        responseHeader = f"r{pin:01d}:"
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

    def digital_read_as_input(self, pin, wait_for_input_time=1):
        """Force INPUT (incl. DAC ALT2 on PA4/5) then read (firmware `R`)."""
        command = f"R{pin:01d}\n"
        responseHeader = f"R{pin:01d}:"
        write_response = self.write_string_wait_for_response(command, responseHeader, wait_for_input_time)
        if (wait_for_input_time == 0):
            return None
        else:
            if (len(write_response)>0):
                try:
                    colon_pos = write_response.find(":")
                    if "not valid" in write_response:
                        return None
                    return (int(write_response[colon_pos+1])>0)
                except:
                    return None
            else:
                return None

    def pin_input(self, pin, wait_for_input_time=0):
        """Release pin to INPUT without clearing matrix (firmware `F`)."""
        command = f"F{pin:01d}\n"
        write_response = self.write_string_wait_for_response(command, f"F{pin:01d}:", wait_for_input_time)
        if (wait_for_input_time == 0):
            return True
        else:
            if (len(write_response)==0):
                return False
            if ("not valid" in write_response):
                return False
            return True

    def logic_analyzer_capture_start(self, rate_hz, sample_count, wait_for_input_time=1):
        command = f"L{rate_hz:08X}{sample_count:08X}\n"
        if (self.serial_port is None):
            return {"ok": False, "error": "Not connected"}
        self.serial_port.write(command.encode("ascii"))
        self.serial_port.flush()
        # Drain until STARTED/ERR; ignore intermediate L: lines from older firmware.
        # Older firmware may stream L:OK/DATA immediately (blocking capture) — treat as started.
        start_time = time.monotonic()
        while (time.monotonic() - start_time < wait_for_input_time):
            time.sleep(0.001)
            for line in self.check_input():
                if (line.startswith("L:ERR,")):
                    return {"ok": False, "error": line[6:]}
                if (line.startswith("L:STARTED,")):
                    try:
                        parts = line.split(",")
                        return {
                            "ok": True,
                            "mode": "async",
                            "sample_count": int(parts[1]),
                            "rate_hz": int(parts[2]),
                        }
                    except (IndexError, ValueError):
                        return {"ok": False, "error": "Bad STARTED line"}
                if (line.startswith("L:OK,")):
                    # Blocking firmware: capture finished and upload is in progress.
                    try:
                        parts = line.split(",")
                        return {
                            "ok": True,
                            "mode": "sync",
                            "sample_count": int(parts[1]),
                            "rate_hz": int(parts[2]),
                            "_prefetch_ok": True,
                        }
                    except (IndexError, ValueError):
                        return {"ok": False, "error": "Bad OK line"}
                if (line.startswith("L:Capture")):
                    # Older banner before OK/DATA — keep waiting.
                    continue
        return {"ok": False, "error": "No response"}

    def _logic_analyzer_process_data_line(self, line, samples):
        colon_pos = line.find(":")
        if (colon_pos < 0):
            return
        for token in line[colon_pos + 1:].split():
            if (len(token) == 2):
                samples.append(int(token, 16))

    def _logic_analyzer_finish_sync_upload(self, actual_sample_count, actual_rate_hz,
                                          wait_for_input_time=5, during_capture=None,
                                          already_in_data=False):
        """Finish reading L:DATA ... L:END after an L:OK from blocking firmware."""
        samples = []
        data_started = already_in_data
        data_done = False
        start_time = time.monotonic()
        while (time.monotonic() - start_time < wait_for_input_time):
            if (during_capture is not None):
                during_capture()
            time.sleep(0.001)
            for line in self.check_input():
                if (line == "L:DATA"):
                    data_started = True
                    continue
                if (line == "L:END"):
                    data_done = True
                    continue
                if (data_started and not data_done):
                    self._logic_analyzer_process_data_line(line, samples)
            if (data_done):
                samples_channels = [[(s >> i) & 1 for s in samples] for i in range(8)]
                return {
                    "ok": True,
                    "sample_count": actual_sample_count,
                    "rate_hz": actual_rate_hz,
                    "samples": samples_channels,
                }
        return {"ok": False, "error": "Timeout waiting for sync upload"}

    def logic_analyzer_capture_poll(self, wait_for_input_time=0.1, during_capture=None):
        if (self.serial_port == None):
            return {"state": "error", "error": "Not connected"}

        self.serial_port.write(b"l\n")
        self.serial_port.flush()

        result_line = None
        actual_sample_count = None
        actual_rate_hz = None
        samples = []
        data_started = False
        data_done = False

        start_time = time.monotonic()
        while (time.monotonic() - start_time < wait_for_input_time):
            if (during_capture is not None):
                during_capture()
            time.sleep(0.001)
            for line in self.check_input():
                if (line == "L:IDLE"):
                    return {"state": "idle"}
                if (line == "L:RUNNING"):
                    return {"state": "running"}
                if (line.startswith("L:ERR,")):
                    return {"state": "error", "error": line[6:]}
                if (line.startswith("L:OK,")):
                    result_line = line
                    try:
                        parts = line.split(",")
                        actual_sample_count = int(parts[1])
                        actual_rate_hz = int(parts[2])
                    except (IndexError, ValueError):
                        return {"state": "error", "error": "Bad OK line"}
                    continue
                if (line == "L:DATA"):
                    data_started = True
                    continue
                if (line == "L:END"):
                    data_done = True
                    continue
                if (data_started and not data_done):
                    self._logic_analyzer_process_data_line(line, samples)

            if (result_line is not None and data_done):
                samples_channels = [[(s >> i) & 1 for s in samples] for i in range(8)]
                return {
                    "state": "done",
                    "sample_count": actual_sample_count,
                    "rate_hz": actual_rate_hz,
                    "samples": samples_channels,
                }

        if (result_line is not None):
            return {"state": "running"}
        return {"state": "timeout"}

    def logic_analyzer_capture_wait(self, sample_count=None, rate_hz=None,
                                    during_capture=None, poll_interval=0.001,
                                    timeout=30):
        if (sample_count is not None and rate_hz is not None and rate_hz > 0):
            capture_timeout = max(timeout, (sample_count / rate_hz) + 2.0)
        else:
            capture_timeout = timeout

        start_time = time.monotonic()
        while (time.monotonic() - start_time < capture_timeout):
            if (during_capture is not None):
                during_capture()
            poll_wait = 0.05
            if (sample_count is not None and rate_hz is not None and rate_hz > 0):
                poll_wait = max(poll_wait, (sample_count / rate_hz) + 2.0)
            poll = self.logic_analyzer_capture_poll(
                wait_for_input_time=poll_wait, during_capture=during_capture)
            if (poll["state"] == "done"):
                return {
                    "ok": True,
                    "sample_count": poll["sample_count"],
                    "rate_hz": poll["rate_hz"],
                    "samples": poll["samples"],
                }
            if (poll["state"] == "error"):
                return {"ok": False, "error": poll["error"]}
            if (poll["state"] == "idle"):
                return {"ok": False, "error": "Capture not running"}
            time.sleep(poll_interval)

        return {"ok": False, "error": "Timeout"}

    def logic_analyzer_capture(self, rate_hz, sample_count, wait_for_input_time=1,
                               during_capture=None):
        """Capture digital LA. Supports async (STARTED+poll) and blocking firmware."""
        if (self.serial_port is None):
            return {"ok": False, "error": "Not connected"}

        # Prefer a single streaming read that handles both firmware styles.
        command = f"L{rate_hz:08X}{sample_count:08X}\n"
        self.serial_port.write(command.encode("ascii"))
        self.serial_port.flush()

        if (sample_count is not None and rate_hz is not None and rate_hz > 0):
            capture_timeout = max(float(wait_for_input_time), (sample_count / rate_hz) + 5.0)
        else:
            capture_timeout = max(float(wait_for_input_time), 30.0)

        actual_sample_count = None
        actual_rate_hz = None
        samples = []
        data_started = False
        data_done = False
        async_started = False

        start_time = time.monotonic()
        while (time.monotonic() - start_time < capture_timeout):
            if (during_capture is not None):
                during_capture()
            time.sleep(0.001)
            for line in self.check_input():
                if (line.startswith("L:ERR,")):
                    return {"ok": False, "error": line[6:]}
                if (line.startswith("L:STARTED,")):
                    try:
                        parts = line.split(",")
                        actual_sample_count = int(parts[1])
                        actual_rate_hz = int(parts[2])
                        async_started = True
                    except (IndexError, ValueError):
                        return {"ok": False, "error": "Bad STARTED line"}
                    # Switch to poll-wait for async firmware.
                    return self.logic_analyzer_capture_wait(
                        sample_count=actual_sample_count,
                        rate_hz=actual_rate_hz,
                        during_capture=during_capture,
                        timeout=capture_timeout,
                    )
                if (line.startswith("L:OK,")):
                    try:
                        parts = line.split(",")
                        actual_sample_count = int(parts[1])
                        actual_rate_hz = int(parts[2])
                    except (IndexError, ValueError):
                        return {"ok": False, "error": "Bad OK line"}
                    continue
                if (line == "L:DATA"):
                    data_started = True
                    continue
                if (line == "L:END"):
                    data_done = True
                    continue
                if (line.startswith("L:Capture")):
                    continue
                if (data_started and not data_done):
                    self._logic_analyzer_process_data_line(line, samples)

            if (actual_sample_count is not None and data_done):
                samples_channels = [[(s >> i) & 1 for s in samples] for i in range(8)]
                return {
                    "ok": True,
                    "sample_count": actual_sample_count,
                    "rate_hz": actual_rate_hz,
                    "samples": samples_channels,
                }

            # Async path: if started but we're somehow still here, poll.
            if (async_started):
                break

        if (actual_sample_count is not None and data_started and not data_done):
            return self._logic_analyzer_finish_sync_upload(
                actual_sample_count, actual_rate_hz,
                wait_for_input_time=5, during_capture=during_capture,
                already_in_data=True)

        return {"ok": False, "error": "Timeout"}

    @staticmethod
    def channel_mask_from_pins(pins):
        mask = 0
        for pin in pins:
            if (pin < 0) or (pin > 7):
                raise ValueError("pin must be 0-7")
            mask |= (1 << pin)
        return mask

    @staticmethod
    def channels_from_mask(channel_mask):
        return [i for i in range(8) if (channel_mask & (1 << i))]

    def analog_capture_start(self, rate_hz, sample_count, channel_mask, wait_for_input_time=1):
        command = f"M{rate_hz:08X}{sample_count:08X}{channel_mask:02X}\n"
        if (self.serial_port is None):
            return {"ok": False, "error": "Not connected"}
        self.serial_port.write(command.encode("ascii"))
        self.serial_port.flush()
        start_time = time.monotonic()
        while (time.monotonic() - start_time < wait_for_input_time):
            time.sleep(0.001)
            for line in self.check_input():
                if (line.startswith("M:ERR,")):
                    return {"ok": False, "error": line[6:]}
                if (line.startswith("M:STARTED,")):
                    try:
                        parts = line.split(",")
                        return {
                            "ok": True,
                            "sample_count": int(parts[1]),
                            "rate_hz": int(parts[2]),
                            "channel_mask": int(parts[3], 16),
                        }
                    except (IndexError, ValueError):
                        return {"ok": False, "error": "Bad STARTED line"}
        return {"ok": False, "error": "No response"}

    def _analog_capture_process_data_line(self, line, time_samples):
        colon_pos = line.find(":")
        if (colon_pos < 0):
            return
        for token in line[colon_pos + 1:].split():
            if (len(token) == 4):
                time_samples.append(int(token, 16))

    def analog_capture_poll(self, wait_for_input_time=0.1, during_capture=None):
        if (self.serial_port == None):
            return {"state": "error", "error": "Not connected"}

        self.serial_port.write(b"m\n")
        self.serial_port.flush()

        result_line = None
        actual_sample_count = None
        actual_rate_hz = None
        actual_channel_mask = None
        time_samples = []
        data_started = False
        data_done = False

        start_time = time.monotonic()
        while (time.monotonic() - start_time < wait_for_input_time):
            if (during_capture is not None):
                during_capture()
            time.sleep(0.001)
            for line in self.check_input():
                if (line == "M:IDLE"):
                    return {"state": "idle"}
                if (line == "M:RUNNING"):
                    return {"state": "running"}
                if (line.startswith("M:ERR,")):
                    return {"state": "error", "error": line[6:]}
                if (line.startswith("M:OK,")):
                    result_line = line
                    try:
                        parts = line.split(",")
                        actual_sample_count = int(parts[1])
                        actual_rate_hz = int(parts[2])
                        actual_channel_mask = int(parts[3], 16)
                    except (IndexError, ValueError):
                        return {"state": "error", "error": "Bad OK line"}
                    continue
                if (line == "M:DATA"):
                    data_started = True
                    continue
                if (line == "M:END"):
                    data_done = True
                    continue
                if (data_started and not data_done):
                    self._analog_capture_process_data_line(line, time_samples)

            if (result_line is not None and data_done):
                channels = self.channels_from_mask(actual_channel_mask)
                num_channels = len(channels)
                samples_by_channel = [[] for _ in channels]
                for time_index in range(0, len(time_samples), num_channels):
                    row = time_samples[time_index:time_index + num_channels]
                    if (len(row) < num_channels):
                        break
                    for ch_index, value in enumerate(row):
                        samples_by_channel[ch_index].append(value)
                return {
                    "state": "done",
                    "sample_count": actual_sample_count,
                    "rate_hz": actual_rate_hz,
                    "channel_mask": actual_channel_mask,
                    "channels": channels,
                    "samples": samples_by_channel,
                }

        if (result_line is not None):
            return {"state": "running"}
        return {"state": "timeout"}

    def analog_capture_wait(self, sample_count=None, rate_hz=None, channel_mask=None,
                            during_capture=None, poll_interval=0.001, timeout=30):
        num_channels = bin(channel_mask).count("1") if channel_mask is not None else 1
        if (sample_count is not None and rate_hz is not None and rate_hz > 0):
            capture_timeout = max(timeout, (sample_count / rate_hz) + 2.0)
        else:
            capture_timeout = timeout

        start_time = time.monotonic()
        while (time.monotonic() - start_time < capture_timeout):
            if (during_capture is not None):
                during_capture()
            poll_wait = 0.05
            if (sample_count is not None and rate_hz is not None and rate_hz > 0):
                poll_wait = max(poll_wait, (sample_count / rate_hz) + 2.0)
            poll = self.analog_capture_poll(
                wait_for_input_time=poll_wait, during_capture=during_capture)
            if (poll["state"] == "done"):
                return {
                    "ok": True,
                    "sample_count": poll["sample_count"],
                    "rate_hz": poll["rate_hz"],
                    "channel_mask": poll["channel_mask"],
                    "channels": poll["channels"],
                    "samples": poll["samples"],
                }
            if (poll["state"] == "error"):
                return {"ok": False, "error": poll["error"]}
            if (poll["state"] == "idle"):
                return {"ok": False, "error": "Capture not running"}
            time.sleep(poll_interval)

        return {"ok": False, "error": "Timeout"}

    def analog_capture(self, rate_hz, sample_count, channel_mask, wait_for_input_time=1,
                       during_capture=None):
        start = self.analog_capture_start(rate_hz, sample_count, channel_mask, wait_for_input_time)
        if (not start["ok"]):
            return start
        return self.analog_capture_wait(
            sample_count=sample_count,
            rate_hz=rate_hz,
            channel_mask=channel_mask,
            during_capture=during_capture,
            timeout=wait_for_input_time,
        )
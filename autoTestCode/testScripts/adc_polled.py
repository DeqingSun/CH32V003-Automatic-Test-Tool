# python3 -m testScripts.adc_polled

import os
import select
import subprocess
import time

from lib.ch32v003_test_target import Ch32V003_test_target

class LineBufferedReader:
    def __init__(self, proc):
        self._proc = proc
        self._buffer = ""

    def _read_chunk(self):
        fd = self._proc.stdout.fileno()
        readable, _, _ = select.select([fd], [], [], 0)
        if readable:
            self._buffer += os.read(fd, 4096).decode()

    def read_complete_lines(self):
        self._read_chunk()
        lines = []
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            lines.append(line.rstrip("\r"))
        return lines

def adc_polled_test():
    test_ch32v003_test_target.connectPin("PD1", "305_PA0")
    test_ch32v003_test_target.connectPin("WCH_LINKE_SWDIO", "305_PA0")

    test_ch32v003_test_target.connectPin("PD4", "305_PA4")

    debug_terminal_command = test_ch32v003_test_target.debug_terminal_command()
    if (debug_terminal_command is False):
        print("Failed to get debug terminal command")
        return False

    debug_terminal_proc = subprocess.Popen(
        debug_terminal_command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    debug_reader = LineBufferedReader(debug_terminal_proc)

    count = 0
    found_adc = False
    while (count < 10 and not found_adc):
        for line in debug_reader.read_complete_lines():
            if ("adc:" in line):
                found_adc = True
                break
        if (not found_adc):
            time.sleep(0.1)
            count += 1

    if (not found_adc):
        print("Failed to find ADC output from debug terminal")
        return False

    test_ch32v003_test_target.test_tool.analog_write(4, 2048) #1/2 of 4096
    time.sleep(0.05)
    for line in debug_reader.read_complete_lines():
        pass #discard all lines

    count = 0
    adc_value = None
    while (count < 10 and adc_value is None):
        for line in debug_reader.read_complete_lines():
            if ("adc:" in line):
                #sample: Count: 2 adc: 507
                adc_value = int(line.split("adc:")[1].strip())
                break
        if (adc_value is None):
            time.sleep(0.1)
            count += 1

    if (adc_value is None):
        print("Failed to find ADC value from debug terminal")
        return False

    #the 003 has 10bit resolution
    if (abs(adc_value-512) < 5):
        print("ADC value in range: ", adc_value)
        return True
    else:
        print("ADC value is not valid: ", adc_value)
        return False

    debug_terminal_proc.terminate()

    return True

if __name__ == "__main__":
    test_ch32v003_test_target = Ch32V003_test_target()
    test_ch32v003_test_target.initialize()
    adc_polled_result = adc_polled_test()
    test_ch32v003_test_target.initialize()
    if (adc_polled_result):
        print("ADC polled test passed")
        exit(0)
    else:
        print("ADC polled test failed")
        exit(1)
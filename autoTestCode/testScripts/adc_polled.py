# python3 -m testScripts.adc_polled

import os
import select
import subprocess
import time

from lib.ch32v003_test_target import Ch32V003_test_target

ADC_TARGET = 512
ADC_TOLERANCE = 8
WAIT_ITERATIONS = 30
WAIT_INTERVAL_S = 0.1
SETTLE_AFTER_DAC_S = 0.1
READ_ADC_WINDOW_S = 1.0


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


def wait_for_adc_line(debug_reader, iterations=WAIT_ITERATIONS):
    for _ in range(iterations):
        for line in debug_reader.read_complete_lines():
            if ("adc:" in line):
                return True
        time.sleep(WAIT_INTERVAL_S)
    return False


def read_last_adc_value(debug_reader, window_s=READ_ADC_WINDOW_S):
    last_adc = None
    deadline = time.monotonic() + window_s
    while (time.monotonic() < deadline):
        for line in debug_reader.read_complete_lines():
            if ("adc:" in line):
                last_adc = int(line.split("adc:")[1].strip())
        time.sleep(0.02)
    return last_adc


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

    try:
        debug_reader = LineBufferedReader(debug_terminal_proc)

        if (not wait_for_adc_line(debug_reader)):
            print("Failed to find ADC output from debug terminal")
            return False

        test_ch32v003_test_target.test_tool.analog_write(4, 2048)  # 1/2 of 4096
        time.sleep(SETTLE_AFTER_DAC_S)

        adc_value = read_last_adc_value(debug_reader)
        if (adc_value is None):
            print("Failed to find ADC value from debug terminal")
            return False

        # the 003 has 10bit resolution
        if (abs(adc_value - ADC_TARGET) <= ADC_TOLERANCE):
            print("ADC value in range: ", adc_value)
            return True
        else:
            print("ADC value is not valid: ", adc_value)
            return False
    finally:
        debug_terminal_proc.terminate()


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
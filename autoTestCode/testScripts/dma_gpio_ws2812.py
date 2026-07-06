# python3 testScripts/dma_gpio_ws2812.py
#
# Tests dma_gpio_ws2812 firmware (PD0, 160 LEDs, 4 time-slices/bit).
# https://github.com/DeqingSun/ch32fun/blob/master/examples/dma_gpio_ws2812/dma_gpio_ws2812.c

import sys
import time
from pathlib import Path

AUTO_TEST_CODE_DIR = Path(__file__).resolve().parents[1]
if str(AUTO_TEST_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(AUTO_TEST_CODE_DIR))

from lib.ch32v003_test_target import Ch32V003_test_target
from lib.ws2812_decoder import decode_ws2812, pixels_between_resets

RATE_HZ = 14_000_000
SAMPLE_COUNT = 128000
LA_CHANNEL = 6
WIRE_ORDER = "GRB"
EXPECTED_LEDS = 160
MIN_RESETS = 2
MAX_CAPTURE_ATTEMPTS = 20
RETRY_DELAY_S = 0.005
SETTLE_AFTER_CONNECT_S = 0.1


def dma_gpio_ws2812_test():
    test_ch32v003_test_target.connectPin("PD0", "305_PA6")
    test_ch32v003_test_target.connectPin("X5", "305_PA6")
    time.sleep(SETTLE_AFTER_CONNECT_S)

    for attempt in range(1, MAX_CAPTURE_ATTEMPTS + 1):
        capture = test_ch32v003_test_target.logic_analyzer_capture(
            RATE_HZ,
            SAMPLE_COUNT,
            wait_for_input_time=30,
        )
        if (capture["ok"] == False):
            print(f"Capture attempt {attempt} failed:", capture["error"])
            time.sleep(RETRY_DELAY_S)
            continue

        channel_data = capture["samples"][LA_CHANNEL]
        result = decode_ws2812(channel_data, capture["rate_hz"], wire_order=WIRE_ORDER)
        frame_pixels = pixels_between_resets(result, WIRE_ORDER)
        led_count = len(frame_pixels)

        print(
            f"Attempt {attempt}: {led_count} LEDs between resets "
            f"(expected {EXPECTED_LEDS}, resets={len(result.resets)})"
        )

        if (len(result.resets) >= MIN_RESETS and led_count == EXPECTED_LEDS):
            return True

        time.sleep(RETRY_DELAY_S)

    print(f"Failed after {MAX_CAPTURE_ATTEMPTS} capture attempts")
    return False


if __name__ == "__main__":
    test_ch32v003_test_target = Ch32V003_test_target()
    test_ch32v003_test_target.initialize()
    test_result = dma_gpio_ws2812_test()
    test_ch32v003_test_target.initialize()
    if (test_result):
        print("dma_gpio_ws2812 test passed")
        exit(0)
    else:
        print("dma_gpio_ws2812 test failed")
        exit(1)

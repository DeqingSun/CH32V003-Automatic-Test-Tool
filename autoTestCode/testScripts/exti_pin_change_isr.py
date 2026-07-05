# python3 testScripts/exti_pin_change_isr.py

import time

from lib.ch32v003_test_target import Ch32V003_test_target

RATE_HZ = 14_000_000
SAMPLE_COUNT = 128000
LA_CHANNEL = 7
PULSE_COUNT = 20
MIN_BLIPS = 4


def count_blips(channel_data, max_width=100):
    blip_count = 0
    in_pulse = False
    pulse_width = 0
    prev = channel_data[0] if len(channel_data) > 0 else 0

    for sample in channel_data[1:]:
        if (not in_pulse and prev == 0 and sample == 1):
            in_pulse = True
            pulse_width = 1
        elif (in_pulse and sample == 1):
            pulse_width += 1
        elif (in_pulse and sample == 0):
            if (pulse_width >= 1 and pulse_width <= max_width):
                blip_count += 1
            in_pulse = False
            pulse_width = 0
        prev = sample

    if (in_pulse):
        return -1
    return blip_count


def exti_pin_change_isr_test():
    test_ch32v003_test_target.connectPin("PD3", "305_PA0")
    test_ch32v003_test_target.connectPin("PC1", "305_PA7")
    test_ch32v003_test_target.connectPin("X6", "305_PA7")

    test_ch32v003_test_target.digital_write(0, False)
    time.sleep(0.01)

    start = test_ch32v003_test_target.logic_analyzer_capture_start(
        RATE_HZ, SAMPLE_COUNT, wait_for_input_time=5
    )
    if (not start["ok"]):
        print(start["error"])
        return False

    pulse_commands = test_ch32v003_test_target.build_digital_pulse_train(0, PULSE_COUNT)
    test_ch32v003_test_target.send_command_batch(pulse_commands)

    capture = test_ch32v003_test_target.logic_analyzer_capture_wait(
        sample_count=SAMPLE_COUNT,
        rate_hz=start["rate_hz"],
        timeout=30,
    )
    if (capture["ok"] == False):
        print(capture["error"])
        return False

    channel_data = capture["samples"][LA_CHANNEL]
    blips = count_blips(channel_data)
    if (blips < 0):
        print("ISR output stuck high during capture window")
        return False
    if (blips < MIN_BLIPS):
        print(f"Expected at least {MIN_BLIPS} blips on PA7, found {blips}")
        return False

    print(f"Detected {blips} EXTI blip(s) on PA7 ({PULSE_COUNT} pulses sent)")
    return True


if __name__ == "__main__":
    test_ch32v003_test_target = Ch32V003_test_target()
    test_ch32v003_test_target.initialize()
    test_result = exti_pin_change_isr_test()
    test_ch32v003_test_target.initialize()
    if (test_result):
        print("EXTI pin change ISR test passed")
        exit(0)
    else:
        print("EXTI pin change ISR test failed")
        exit(1)

# python3 testScripts/exti_pin_change_isr.py

import time

from lib.ch32v003_test_target import Ch32V003_test_target

RATE_HZ = 14_000_000
SAMPLE_COUNT = 128000
LA_CHANNEL = 7
PULSE_COUNT = 20
MIN_BLIPS = 4
RISE_PERIOD_S = 0.0004
LOW_BEFORE_RISE_S = 0.00015


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


def build_pulse_schedule(pulse_count):
    events = []
    for index in range(pulse_count):
        t_rise = 0.001 + index * RISE_PERIOD_S
        events.append((t_rise - LOW_BEFORE_RISE_S, False))
        events.append((t_rise, True))
    return events


def exti_pin_change_isr_test():
    test_ch32v003_test_target.connectPin("PD3", "305_PA0")
    test_ch32v003_test_target.connectPin("PC1", "305_PA7")
    test_ch32v003_test_target.connectPin("X6", "305_PA7")

    test_ch32v003_test_target.digital_write(0, False)
    time.sleep(0.01)

    pulse_events = build_pulse_schedule(PULSE_COUNT)
    stimulus = {"start": None, "index": 0, "rising_edges": 0}

    def pulse_pd3():
        if (stimulus["start"] is None):
            return
        elapsed = time.monotonic() - stimulus["start"]
        while (stimulus["index"] < len(pulse_events)):
            when, value = pulse_events[stimulus["index"]]
            if (elapsed < when):
                break
            test_ch32v003_test_target.digital_write(0, value)
            if (value):
                stimulus["rising_edges"] += 1
            stimulus["index"] += 1

    start = test_ch32v003_test_target.logic_analyzer_capture_start(
        RATE_HZ, SAMPLE_COUNT, wait_for_input_time=5
    )
    if (not start["ok"]):
        print(start["error"])
        return False

    stimulus["start"] = time.monotonic()
    capture = test_ch32v003_test_target.logic_analyzer_capture_wait(
        sample_count=SAMPLE_COUNT,
        rate_hz=start["rate_hz"],
        during_capture=pulse_pd3,
        timeout=30,
    )
    if (capture["ok"] == False):
        print(capture["error"])
        return False

    if (stimulus["rising_edges"] < PULSE_COUNT):
        print(
            f"Sent {stimulus['rising_edges']}/{PULSE_COUNT} rising-edge stimuli during capture"
        )
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

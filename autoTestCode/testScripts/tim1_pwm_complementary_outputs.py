# python3 testScripts/tim1_pwm_complementary_outputs.py

import time

from lib.ch32v003_test_target import Ch32V003_test_target

RATE_HZ = 640_000
SAMPLE_COUNT = 128000
PWM_PERIOD_S = 2.083e-3
CH1_CHANNEL = 6
CH1N_CHANNEL = 3
PERIOD_TOLERANCE = 0.25
MIN_RUN_SAMPLES = 50
MIN_VALID_RUNS = 10
BOTH_HIGH_MAX_FRACTION = 0.01
ACTIVE_OPPOSITE_MIN = 0.99
DEADTIME_HALF_DELTA_MIN = 0.40
DEADTIME_RECAPTURE_DELAY_S = 2.56
DEADTIME_MEDIAN_DELTA_MIN = 2
PWM_TRIM_FRACTION = 0.25


def measure_level_runs(channel_data):
    if (len(channel_data) == 0):
        return []
    signal_level = channel_data[0]
    duration_count = 0
    runs = []
    for sample in channel_data:
        if (sample == signal_level):
            duration_count += 1
        else:
            runs.append(duration_count)
            duration_count = 1
            signal_level = 1 - signal_level
    runs.append(duration_count)
    return runs


def verify_pwm_channel(channel_data, rate_hz, channel_name):
    runs = measure_level_runs(channel_data)
    if (len(runs) < 4):
        print(f"{channel_name}: not enough level runs")
        return False

    expected_half_period = rate_hz * PWM_PERIOD_S / 2.0
    half_min = expected_half_period * (1.0 - PERIOD_TOLERANCE)
    half_max = expected_half_period * (1.0 + PERIOD_TOLERANCE)

    valid_runs = [
        duration for duration in runs[1:-1]
        if (duration >= MIN_RUN_SAMPLES and half_min <= duration <= half_max)
    ]
    if (len(valid_runs) < MIN_VALID_RUNS):
        print(
            f"{channel_name}: only {len(valid_runs)} valid half-period runs "
            f"(need {MIN_VALID_RUNS}, expected ~{expected_half_period:.0f} samples)"
        )
        return False

    return True


def verify_complementary(ch1, ch3):
    if (len(ch1) == 0 or len(ch1) != len(ch3)):
        print("Complementary check: channel length mismatch")
        return False

    both_high = sum(1 for index in range(len(ch1)) if (ch1[index] == 1 and ch3[index] == 1))
    both_high_fraction = both_high / len(ch1)
    if (both_high_fraction > BOTH_HIGH_MAX_FRACTION):
        print(
            f"Complementary check: both-high fraction {both_high_fraction:.6f} "
            f"exceeds {BOTH_HIGH_MAX_FRACTION}"
        )
        return False

    active_indices = [index for index in range(len(ch1)) if (ch1[index] or ch3[index])]
    if (len(active_indices) == 0):
        print("Complementary check: no active samples")
        return False

    opposite = sum(
        1 for index in active_indices if (ch1[index] != ch3[index])
    ) / len(active_indices)
    if (opposite < ACTIVE_OPPOSITE_MIN):
        print(f"Complementary opposite fraction {opposite:.4f} below {ACTIVE_OPPOSITE_MIN}")
        return False

    return True


def median_half_period(channel_data, rate_hz):
    runs = measure_level_runs(channel_data)
    if (len(runs) < 4):
        return None

    expected_half_period = rate_hz * PWM_PERIOD_S / 2.0
    half_min = expected_half_period * (1.0 - PERIOD_TOLERANCE)
    half_max = expected_half_period * (1.0 + PERIOD_TOLERANCE)
    valid_runs = [
        duration for duration in runs[1:-1]
        if (duration >= MIN_RUN_SAMPLES and half_min <= duration <= half_max)
    ]
    if (len(valid_runs) == 0):
        return None
    return sorted(valid_runs)[len(valid_runs) // 2]


def verify_deadtime_sweep(target, ch1_full, ch3_full, rate_hz, first_median_half_period):
    midpoint = len(ch1_full) // 2
    first_half_both_low = sum(
        1 for index in range(midpoint) if (ch1_full[index] == 0 and ch3_full[index] == 0)
    ) / midpoint
    second_half_both_low = sum(
        1 for index in range(midpoint, len(ch1_full)) if (ch1_full[index] == 0 and ch3_full[index] == 0)
    ) / (len(ch1_full) - midpoint)
    half_delta = abs(first_half_both_low - second_half_both_low)

    if (half_delta >= DEADTIME_HALF_DELTA_MIN):
        print(
            f"Deadtime sweep ok: both-low first half={first_half_both_low:.4f}, "
            f"second half={second_half_both_low:.4f}"
        )
        return True

    time.sleep(DEADTIME_RECAPTURE_DELAY_S)
    recapture = target.logic_analyzer_capture(RATE_HZ, SAMPLE_COUNT, wait_for_input_time=30)
    if (recapture["ok"] == False):
        print("Deadtime sweep recapture failed:", recapture["error"])
        return False

    trim_index = int(len(recapture["samples"][CH1_CHANNEL]) * PWM_TRIM_FRACTION)
    second_median = median_half_period(
        recapture["samples"][CH1_CHANNEL][trim_index:],
        recapture["rate_hz"],
    )
    if (first_median_half_period is None or second_median is None):
        print("Deadtime sweep: could not measure median half-period")
        return False

    median_delta = abs(second_median - first_median_half_period)
    if (median_delta < DEADTIME_MEDIAN_DELTA_MIN):
        print(
            "Deadtime sweep: median half-period unchanged "
            f"({first_median_half_period} vs {second_median})"
        )
        return False

    print(
        f"Deadtime sweep ok via recapture: median half-period "
        f"{first_median_half_period} -> {second_median}"
    )
    return True


def tim1_pwm_complementary_outputs_test():
    test_ch32v003_test_target.connectPin("PC6", "305_PA6")
    test_ch32v003_test_target.connectPin("PC3", "305_PA3")

    capture = test_ch32v003_test_target.logic_analyzer_capture(
        RATE_HZ,
        SAMPLE_COUNT,
        wait_for_input_time=30,
    )
    if (capture["ok"] == False):
        print(capture["error"])
        return False

    rate_hz = capture["rate_hz"]
    trim_index = int(len(capture["samples"][CH1_CHANNEL]) * PWM_TRIM_FRACTION)
    ch1 = capture["samples"][CH1_CHANNEL][trim_index:]
    ch1n = capture["samples"][CH1N_CHANNEL][trim_index:]

    if (not verify_pwm_channel(ch1, rate_hz, "CH1 PC6")):
        return False
    if (not verify_pwm_channel(ch1n, rate_hz, "CH1N PC3")):
        return False
    if (not verify_complementary(ch1, ch1n)):
        return False

    first_median = median_half_period(ch1, rate_hz)
    if (not verify_deadtime_sweep(
        test_ch32v003_test_target,
        capture["samples"][CH1_CHANNEL],
        capture["samples"][CH1N_CHANNEL],
        rate_hz,
        first_median,
    )):
        return False

    return True


if __name__ == "__main__":
    test_ch32v003_test_target = Ch32V003_test_target()
    test_ch32v003_test_target.initialize()
    test_result = tim1_pwm_complementary_outputs_test()
    test_ch32v003_test_target.initialize()
    if (test_result):
        print("TIM1 complementary PWM test passed")
        exit(0)
    else:
        print("TIM1 complementary PWM test failed")
        exit(1)

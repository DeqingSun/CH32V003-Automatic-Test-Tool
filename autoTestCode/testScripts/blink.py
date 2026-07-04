# python3 testScripts/blink.py

from lib.ch32v003_test_target import Ch32V003_test_target

def blink_test():
    test_ch32v003_test_target.connectPin("PD0", "305_PA7")
    test_ch32v003_test_target.connectPin("X6", "305_PA7")

    logic_analyzer_capture = test_ch32v003_test_target.logic_analyzer_capture(1000, 1000)   #sample rate, sample count
    if (logic_analyzer_capture["ok"] == False):
        print(logic_analyzer_capture["error"])
        return False

    # since the PD0 of CH32V003 is connected to the PA7, check the high and low level duration of the logic analyzer capture
    # the PD0 toggle every 250ms, and the logic analyzer capture is 1000 samples at 1000Hz, so each sample is 1ms
    # discard the duration before the first edge and after the last edge, and count the number of samples in the high and low level
    channel_data = logic_analyzer_capture["samples"][0]
    signalLevel = channel_data[0]
    durationSamples = []
    durationCount = 0
    for sample in channel_data:
        if (sample == signalLevel):
            durationCount += 1
        else:
            durationSamples.append(durationCount)
            durationCount = 0
            signalLevel = 1 - signalLevel
    durationSamples.append(durationCount)
    #discard the first and last duration
    durationSamples = durationSamples[1:-1]
    for duration in durationSamples:
        if (duration < 240 or duration > 260):
            print(f"Duration {duration} is not allowed")
            return False
    return True

if __name__ == "__main__":
    test_ch32v003_test_target = Ch32V003_test_target()
    test_ch32v003_test_target.initialize()
    blink_result = blink_test()
    test_ch32v003_test_target.initialize()
    if (blink_result):
        print("Blink test passed")
        exit(0)
    else:
        print("Blink test failed")
        exit(1)

from ch32v003_test_target import Ch32V003_test_target

test_ch32v003_test_target = Ch32V003_test_target()
test_ch32v003_test_target.initialize()
test_ch32v003_test_target.connectPin("PD0", "304_PA7")
test_ch32v003_test_target.connectPin("X6", "304_PA7")

logic_analyzer_capture = test_ch32v003_test_target.logic_analyzer_capture(1000, 100)   #sample rate, sample count
print(logic_analyzer_capture)
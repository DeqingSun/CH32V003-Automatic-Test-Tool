from lib.ch32v003_test_target import Ch32V003_test_target
from lib.logic_analyzer_util import LogicAnalyzerUtil

test_ch32v003_test_target = Ch32V003_test_target()
test_ch32v003_test_target.initialize()
test_ch32v003_test_target.connectPin("PD0", "304_PA7")
test_ch32v003_test_target.connectPin("X6", "304_PA7")

logic_analyzer_capture = test_ch32v003_test_target.logic_analyzer_capture(1000, 1000)   #sample rate, sample count
if (logic_analyzer_capture["ok"] == False):
    print(logic_analyzer_capture["error"])
    exit(1)

logic_analyzer_util = LogicAnalyzerUtil(logic_analyzer_capture)
fig = logic_analyzer_util.plot_logic_analyzer_capture(6,6)
fig.savefig("logic_analyzer_capture.png")

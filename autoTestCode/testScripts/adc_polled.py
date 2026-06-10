# python3 -m testScripts.adc_polled

from lib.ch32v003_test_target import Ch32V003_test_target
from lib.logic_analyzer_util import LogicAnalyzerUtil

def adc_polled_test():
    test_ch32v003_test_target.connectPin("PD1", "305_PA0")
    test_ch32v003_test_target.connectPin("WCH_LINKE_SWDIO", "305_PA0")

    debug_terminal_command = test_ch32v003_test_target.debug_terminal_command()
    if (debug_terminal_command is False):
        print("Failed to get debug terminal command")
        return False
    #print(debug_terminal_command)



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
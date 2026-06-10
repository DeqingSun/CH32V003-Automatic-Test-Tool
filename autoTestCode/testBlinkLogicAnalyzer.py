from lib.ch32v003_test_target import Ch32V003_test_target

test_ch32v003_test_target = Ch32V003_test_target()
test_ch32v003_test_target.initialize()
test_ch32v003_test_target.connectPin("PD0", "304_PA7")
test_ch32v003_test_target.connectPin("X6", "304_PA7")

logic_analyzer_capture = test_ch32v003_test_target.logic_analyzer_capture(1000, 1000)   #sample rate, sample count
if (logic_analyzer_capture["ok"] == False):
    print(logic_analyzer_capture["error"])
    exit(1)

import matplotlib.pyplot as plt

# Resistor color code: digit 0–7 maps to PA0–PA7
RESISTOR_COLORS = [
    "#1a1a1a",  # 0 black
    "#8B4513",  # 1 brown
    "#E60000",  # 2 red
    "#FF8C00",  # 3 orange
    "#D4AF00",  # 4 yellow
    "#228B22",  # 5 green
    "#1040C0",  # 6 blue
    "#7B2D8E",  # 7 violet
]

sample_count = logic_analyzer_capture["sample_count"]
rate_hz = logic_analyzer_capture["rate_hz"]
time_ms = [i * 1000.0 / rate_hz for i in range(sample_count)]

fig, axes = plt.subplots(8, 1, sharex=True, figsize=(10, 6))
for i, ax in enumerate(axes):
    color = RESISTOR_COLORS[i]
    ax.plot(time_ms, logic_analyzer_capture["samples"][i], color=color)
    ax.set_ylabel(f"PA{i}", fontsize=8, color=color)
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 1])
    ax.tick_params(axis="y", labelsize=8)
axes[-1].set_xlabel("Time (ms)")
fig.tight_layout()
plt.show()
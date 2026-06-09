from ch32v003_test_target import Ch32V003_test_target

test_ch32v003_test_target = Ch32V003_test_target()
test_ch32v003_test_target.initialize()
test_ch32v003_test_target.connectPin("PD0", "304_PA7")
test_ch32v003_test_target.connectPin("X6", "304_PA7")

logic_analyzer_capture = test_ch32v003_test_target.logic_analyzer_capture(1000, 1000)   #sample rate, sample count
if (logic_analyzer_capture["ok"] == False):
    print(logic_analyzer_capture["error"])
    exit(1)

import matplotlib.pyplot as plt

fig, axes = plt.subplots(8, 1, sharex=True, figsize=(10, 6))
for i, ax in enumerate(axes):
    ax.plot(logic_analyzer_capture["samples"][i])
    ax.set_ylabel(f"PA{i}", fontsize=8)
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 1])
    ax.tick_params(axis="y", labelsize=8)
axes[-1].set_xlabel("Sample")
fig.tight_layout()
plt.show()
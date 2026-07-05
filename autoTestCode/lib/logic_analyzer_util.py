class LogicAnalyzerUtil:
    def __init__(self, logic_analyzer_capture):
        self.logic_analyzer_capture = logic_analyzer_capture

    def plot_logic_analyzer_capture(self, xSize=10, ySize=10):
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

        sample_count = self.logic_analyzer_capture["sample_count"]
        rate_hz = self.logic_analyzer_capture["rate_hz"]
        time_ms = [i * 1000.0 / rate_hz for i in range(sample_count)]

        fig, axes = plt.subplots(8, 1, sharex=True, figsize=(xSize, ySize))
        for i, ax in enumerate(axes):
            color = RESISTOR_COLORS[i]
            ax.plot(time_ms, self.logic_analyzer_capture["samples"][i], color=color)
            ax.set_ylabel(f"PA{i}", fontsize=8, color=color)
            ax.set_ylim(-0.1, 1.1)
            ax.set_yticks([0, 1])
            ax.tick_params(axis="y", labelsize=8)
        axes[-1].set_xlabel("Time (ms)")
        fig.tight_layout()
        return fig

    def plot_analog_capture(self, xSize=10, ySize=10):
        import matplotlib.pyplot as plt

        RESISTOR_COLORS = [
            "#1a1a1a",
            "#8B4513",
            "#E60000",
            "#FF8C00",
            "#D4AF00",
            "#228B22",
            "#1040C0",
            "#7B2D8E",
        ]

        sample_count = self.logic_analyzer_capture["sample_count"]
        rate_hz = self.logic_analyzer_capture["rate_hz"]
        channels = self.logic_analyzer_capture["channels"]
        samples = self.logic_analyzer_capture["samples"]
        time_ms = [i * 1000.0 / rate_hz for i in range(sample_count)]

        channel_count = len(channels)
        fig, axes = plt.subplots(channel_count, 1, sharex=True, figsize=(xSize, ySize))
        if (channel_count == 1):
            axes = [axes]

        for index, ax in enumerate(axes):
            channel = channels[index]
            color = RESISTOR_COLORS[channel]
            ax.plot(time_ms, samples[index], color=color)
            ax.set_ylabel(f"PA{channel}", fontsize=8, color=color)
            ax.set_ylim(-100, 4200)
            ax.tick_params(axis="y", labelsize=8)

        axes[-1].set_xlabel("Time (ms)")
        fig.tight_layout()
        return fig
        
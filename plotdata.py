import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


class matedata:
    def __init__(self, prefix):
        self.prefix = prefix
        self.date = []  # datetime entries
        self.mates = []  # mates
        self.bmates = []  # best mates
        with open(prefix + ".csv") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Commit"):  # ignore the header
                    continue
                if line:
                    parts = line.split(",")
                    self.date.append(datetime.fromisoformat(parts[0]))
                    self.total = int(parts[2])
                    self.mates.append(int(parts[3]))
                    self.bmates.append(int(parts[4]))

    def create_graph(self, plotAll=False):
        plotStart = 0 if plotAll else -50
        d, m, b = self.date[plotStart:], self.mates[plotStart:], self.bmates[plotStart:]
        dotSize, lineWidth = (20, 0.5) if len(d) < 1000 else (5, 0.0)
        fig, ax = plt.subplots()
        yColor, dateColor = "black", "black"
        bmateColor, mateColor = "limegreen", "blue"
        ax.scatter(d, m, label="mates", color=mateColor, s=dotSize)
        ax.scatter(d, b, label="best mates", color=bmateColor, s=dotSize)
        ax.plot(d, m, color=mateColor, linewidth=lineWidth)
        ax.plot(d, b, color=bmateColor, linewidth=lineWidth)
        ax.set_ylabel("# of mates", color=yColor)
        ax.tick_params(axis="y", labelcolor=yColor)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.setp(
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
            rotation_mode="anchor",
            fontsize=6,
        )
        ax.legend()
        fig.suptitle("Evolution of SF mate finding effectiveness")
        nodes = self.prefix[9:]  #  this will only work for "matetrackXXX"
        if nodes.endswith("0" * 9):
            nodes = nodes[:-9] + "G"  #  :)
        elif nodes.endswith("0" * 6):
            nodes = nodes[:-6] + "M"
        elif nodes.endswith("0" * 3):
            nodes = nodes[:-3] + "K"
        ax.set_title(
            f"(Mates found with {nodes} nodes per position on matetrack.epd"
            + (f" for last {-plotStart} commits.)" if not plotAll else ".)"),
            fontsize=6,
            family="monospace",
        )
        plt.savefig(self.prefix + ("all" if plotAll else "") + ".png", dpi=300)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot data stored in e.g. matetrack1000000.csv.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="file with statistics over time",
        default="matetrack1000000.csv",
    )
    args = parser.parse_args()

    prefix, _, _ = args.filename.partition(".csv")
    data = matedata(prefix)
    data.create_graph()
    data.create_graph(plotAll=True)

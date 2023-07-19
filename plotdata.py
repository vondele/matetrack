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
        self.tags = []  # possible release tags
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
                    self.tags.append(parts[5])

    def create_graph(self, plotAll=False):
        # plotAll=True: full history, against date, single y-axis
        # plotAll=False: last 50 commits, against commit, two y-axes
        plotStart = 0 if plotAll else -50
        d, m, b, t = (
            self.date[plotStart:],
            self.mates[plotStart:],
            self.bmates[plotStart:],
            self.tags[plotStart:],
        )
        fig, ax = plt.subplots()
        yColor, dateColor = "black", "black"
        bmateColor, mateColor = "limegreen", "blue"
        if plotAll:
            dotSize = 1
            bmate = ax.scatter(d, m, label="mates", color=mateColor, s=dotSize)
            mate = ax.scatter(d, b, label="best mates", color=bmateColor, s=dotSize)
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
            ax.grid(alpha=0.4, linewidth=0.5)
            lgnd = ax.legend()
            for handle in lgnd.legendHandles:
                handle.set_sizes([8])
            bmate.set_alpha(0.25)
            mate.set_alpha(0.25)
        else:
            d = list(range(plotStart + 1, 1))
            ax2 = ax.twinx()
            bmateDotSize, bmateLineWidth = 25, 0.75
            mateDotSize, mateLineWidth, mateAlpha = 5, 0.2, 0.5
            ax2.scatter(
                d, m, label="mates", color=mateColor, s=mateDotSize, alpha=mateAlpha
            )
            ax.scatter(d, b, label="best mates", color=bmateColor, s=bmateDotSize)
            ax2.plot(d, m, color=mateColor, linewidth=mateLineWidth, alpha=mateAlpha)
            ax.plot(d, b, color=bmateColor, linewidth=bmateLineWidth)
            ax.set_ylabel("# of best mates", color=bmateColor)
            ax.tick_params(axis="y", labelcolor=bmateColor)
            ax2.set_ylabel("# of mates", color=mateColor)
            ax2.tick_params(axis="y", labelcolor=mateColor, labelsize=7)
        # add release labels
        for i, txt in enumerate(t):
            if txt:
                ax.annotate(
                    txt,
                    xy=(d[i], b[i]),
                    xycoords="data",
                    xytext=(-7, 30 - plotAll * 60),
                    textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color="black"),
                    fontsize=5,
                    weight="bold",
                )
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

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
        self.issues = []  # sum of better mates, wrong mates, bad PVs
        self.tags = []  # possible release tags
        with open(prefix + ".csv") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Commit"):  # ignore the header
                    continue
                if line:
                    parts = line.split(",")
                    if parts[2]:  # ignore skipped commits
                        self.date.append(datetime.fromisoformat(parts[0]))
                        self.mates.append(int(parts[3]))
                        self.bmates.append(int(parts[4]))
                        self.issues.append(
                            sum(int(parts[i]) for i in [5, 6, 7] if parts[i])
                        )
                        self.tags.append(parts[-1])

    def create_graph(self, plotAll=False):
        # plotAll=True: full history, against date, single y-axis
        # plotAll=False: last 50 commits, against commit, two y-axes
        plotStart = 0 if plotAll else -50
        d, m, b, i, t = (
            self.date[plotStart:],
            self.mates[plotStart:],
            self.bmates[plotStart:],
            self.issues[plotStart:],
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
            # increase the size of the two dots in the legend
            # legendHandles will cease to work from Matplotlib v3.9.0: legend_handles may then work
            lgnd = ax.legend()
            for handle in lgnd.legendHandles:
                handle.set_sizes([8])
            # now reduce opacity for the dots in the plot itself
            bmate.set_alpha(0.25)
            mate.set_alpha(0.25)
        else:
            d = list(range(1 - len(d), 1))
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
            if sum(i):
                color, label = (
                    ("red", "needs investigation")
                    if i[-1]
                    else ("orange", "needed investigation")
                )
                issueIdx = [idx for idx, val in enumerate(i) if val]
                ax2.scatter(
                    [d[idx] for idx in issueIdx],
                    [m[idx] for idx in issueIdx],
                    label=label,
                    color=color,
                    s=bmateDotSize,
                )
                ax2.legend()

        # add release labels
        for i, txt in enumerate(t):
            if txt:
                shortArrow = txt in ["sf_13", "sf_14.1"]
                ax.annotate(
                    txt,
                    xy=(d[i], b[i]),
                    xycoords="data",
                    xytext=(-7, 30 - plotAll * (60 - shortArrow * 5)),
                    textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color="black"),
                    fontsize=5,
                    weight="bold",
                )

        # add GOAT labels
        for dataset in [self.mates, self.bmates]:
            maxValue = max(dataset)
            maxIndex = dataset.index(maxValue)
            usedAxis = ax2 if not plotAll and dataset == self.mates else ax
            usedAxis.annotate(
                "GOAT",
                xy=(
                    self.date[maxIndex] if plotAll else maxIndex - len(dataset),
                    dataset[maxIndex],
                ),
                xycoords="data",
                xytext=(-30, 0),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="black"),
                fontsize=5,
                weight="bold",
            )
            if plotAll:
                continue
            usedAxis.axhline(
                maxValue, color="silver", linestyle="dashed", linewidth=0.2
            )
            yt = list(usedAxis.get_yticks())
            ytGap = yt[1] - yt[0] if len(yt) > 1 else 0
            if min(dataset[plotStart:]) > yt[1]:
                yt.pop(0)
            usedAxis.set_yticks(
                [t for t in yt if t < maxValue - 0.5 * ytGap] + [maxValue]
            )

        fig.suptitle("Evolution of SF mate finding effectiveness")
        nodes = self.prefix[len(self.prefix.rstrip("0123456789")) :]
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

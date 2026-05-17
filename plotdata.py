import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


class matedata:
    def __init__(self, prefix):
        self.prefix = prefix
        self.dates = []  # datetime entries
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
                    mates, bmates, issues = (
                        (
                            int(parts[3]),
                            int(parts[4]),
                            sum(int(parts[i]) for i in [5, 6, 7] if parts[i]),
                        )
                        if parts[2]
                        else (None,) * 3
                    )
                    self.dates.append(datetime.fromisoformat(parts[0]))
                    self.mates.append(mates)
                    self.bmates.append(bmates)
                    self.issues.append(issues)
                    self.tags.append(parts[-1])

    def create_graph(self, epdName, plotAll=False, showGoatLines=False):
        # plotAll=True: full history, against date, single y-axis
        # plotAll=False: last 50 commits, against commit, two y-axes
        plotStart = 0 if plotAll else -50
        dates, mates, bmates, issues, tags = (
            self.dates[plotStart:],
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
            axms = ax.scatter(dates, mates, label="mates", color=mateColor, s=dotSize)
            axbms = ax.scatter(
                dates, bmates, label="best mates", color=bmateColor, s=dotSize
            )
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
            ax.grid(axis="y", alpha=0.4, linewidth=0.5)
            # increase the size of the two dots in the legend
            lgnd = ax.legend()
            try:
                handles = lgnd.legend_handles
            except AttributeError:
                handles = lgnd.legendHandles
            for handle in handles:
                handle.set_sizes([8])
            # now reduce opacity for the dots in the plot itself
            for a in [axms, axbms]:
                a.set_alpha(0.25)
        else:
            dates = list(range(1 - len(dates), 1))
            ax2 = ax.twinx()
            bmateDotSize, bmateLineWidth = 25, 0.75
            mateDotSize, mateLineWidth, mateAlpha = 5, 0.2, 0.5
            ax2.scatter(
                dates,
                mates,
                label="mates",
                color=mateColor,
                s=mateDotSize,
                alpha=mateAlpha,
            )
            ax.scatter(
                dates, bmates, label="best mates", color=bmateColor, s=bmateDotSize
            )
            ax2.plot(
                dates, mates, color=mateColor, linewidth=mateLineWidth, alpha=mateAlpha
            )
            ax.plot(dates, bmates, color=bmateColor, linewidth=bmateLineWidth)
            ax.set_ylabel("# of best mates", color=bmateColor)
            ax.tick_params(axis="y", labelcolor=bmateColor)
            ax2.set_ylabel("# of mates", color=mateColor)
            ax2.tick_params(axis="y", labelcolor=mateColor, labelsize=7)
            if sum(v for v in issues if v is not None):
                color, label = (
                    ("red", "needs investigation")
                    if issues[-1]
                    else ("orange", "needed investigation")
                )
                issueIdx = [idx for idx, val in enumerate(issues) if val]
                ax2.scatter(
                    [dates[idx] for idx in issueIdx],
                    [mates[idx] for idx in issueIdx],
                    label=label,
                    color=color,
                    s=bmateDotSize,
                )
                ax2.legend()
            for Idx, (s, dat, col) in enumerate(
                [("best mates", bmates, bmateColor), ("mates", mates, mateColor)]
            ):
                cleandat = [d for d in dat if d is not None]
                datmin, datmax = min(cleandat), max(cleandat)
                datmean = (datmin + datmax) // 2
                datpct = datmax * 100 / max(datmean, 1) - 100
                datStr = f"{s}$\subset$[{datmin},{datmax}]$\\approx${datmean}$\pm${datpct:.1f}%"
                lenStr = len(datStr) - 20  # account for LaTeX commands
                ax.text(
                    0.055 + Idx * (0.94 - 0.012 * lenStr),
                    0.02,
                    datStr,
                    transform=fig.transFigure,
                    color=col,
                    fontsize=7,
                    family="monospace",
                    weight="bold",
                )

        ymin, ymax = ax.get_ylim()
        ytext, va = (ymax, "top") if epdName == "classic280" else (ymin, "bottom")

        # add release labels
        for i, txt in enumerate(tags):
            if txt:
                ax.axvline(
                    x=dates[i], color="gray", linestyle="--", linewidth=0.5, alpha=0.5
                )

                ax.annotate(
                    " " + txt,
                    xy=(dates[i], ytext),
                    rotation=90,
                    ha="center",
                    va=va,
                    fontsize=5,
                )

        # add GOAT labels
        for dataset in [self.mates, self.bmates]:
            maxValue = max(m for m in dataset if m is not None)
            maxIndex = dataset.index(maxValue)
            usedAxis = ax2 if not plotAll and dataset == self.mates else ax
            usedAxis.annotate(
                "GOAT",
                xy=(
                    self.dates[maxIndex] if plotAll else 1 + maxIndex - len(dataset),
                    dataset[maxIndex],
                ),
                xycoords="data",
                xytext=(-30, 5 - 12 * bool(epdName == "classic280")),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="black"),
                fontsize=5,
                weight="bold",
            )
            if plotAll or not showGoatLines:
                continue
            usedAxis.axhline(
                maxValue, color="silver", linestyle="dashed", linewidth=0.2
            )
            yt = list(usedAxis.get_yticks())
            ytGap = yt[1] - yt[0] if len(yt) > 1 else 0
            if min(m for m in dataset[plotStart:] if m is not None) > yt[1]:
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
            f"(Mates found with {nodes} nodes per position on {epdName}.epd"
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
    epdName = "classic280" if prefix[:7] == "classic" else "matetrack"
    data.create_graph(epdName, showGoatLines=False)
    data.create_graph(epdName, plotAll=True)

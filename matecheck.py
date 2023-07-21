import argparse, re, concurrent.futures, chess, chess.engine
from time import time
from multiprocessing import freeze_support, cpu_count
from tqdm import tqdm


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class Analyser:
    def __init__(self, engine, nodes):
        self.engine = engine
        self.nodes = nodes

    def analyze_fens(self, fens):
        result_fens = []
        engine = chess.engine.SimpleEngine.popen_uci(self.engine)
        for fen, bm in fens:
            board = chess.Board(fen)
            info = engine.analyse(
                board, chess.engine.Limit(nodes=self.nodes), game=board
            )
            m = info["score"].pov(board.turn).mate() if "score" in info else None
            result_fens.append((fen, bm, m))

        engine.quit()

        return result_fens


if __name__ == "__main__":
    freeze_support()
    parser = argparse.ArgumentParser(
        description="Check how many (best) mates an engine finds in e.g. matetrack.epd.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--engine",
        default="./stockfish",
        help="name of the engine binary",
    )
    parser.add_argument("--nodes", type=int, default=10**6, help="nodes per position")
    parser.add_argument(
        "--epdFile",
        default="matetrack.epd",
        help="file containing the positions and their mate scores",
    )
    args = parser.parse_args()

    ana = Analyser(args.engine, args.nodes)

    p = re.compile("([0-9a-zA-Z/\- ]*) bm #([0-9\-]*);")
    fens = []

    print("Loading FENs...")

    with open(args.epdFile) as f:
        for line in f:
            m = p.match(line)
            if not m:
                print("---------------------> IGNORING : ", line)
            else:
                fens.append((m.group(1), int(m.group(2))))

    print("FENs loaded...")

    numfen = len(fens)
    workers = cpu_count()
    fw_ratio = numfen // (4 * workers)
    fenschunked = list(chunks(fens, max(1, fw_ratio)))

    print("\nMatetrack started...")

    res = []
    futures = []

    with tqdm(total=len(fenschunked), smoothing=0, miniters=1) as pbar:
        with concurrent.futures.ProcessPoolExecutor() as e:
            for entry in fenschunked:
                futures.append(e.submit(ana.analyze_fens, entry))

            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)
                res += future.result()

    mates = bestmates = 0
    for _, bestmate, mate in res:
        if mate is not None and mate * bestmate > 0:
            mates += 1
            if mate == bestmate:
                bestmates += 1

    print("Using %s with %d nodes" % (args.engine, args.nodes))
    print("Total fens:   ", numfen)
    print("Found mates:  ", mates)
    print("Best mates:   ", bestmates)

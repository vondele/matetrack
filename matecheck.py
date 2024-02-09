import argparse, re, concurrent.futures, chess, chess.engine
from time import time
from multiprocessing import freeze_support, cpu_count
from tqdm import tqdm


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def pv_status(fen, mate, pv):
    # check if the given pv (list of uci moves) leads to checkmate #mate
    plies_to_checkmate = 2 * mate - 1 if mate > 0 else -2 * mate
    if len(pv) < plies_to_checkmate:
        return "short"
    if len(pv) > plies_to_checkmate:
        return "long"
    board = chess.Board(fen)
    losing_side = 1 if mate > 0 else 0
    try:
        for ply, move in enumerate(pv):
            if ply % 2 == losing_side and board.can_claim_draw():
                return "draw"
            board.push(chess.Move.from_uci(move))
        if board.is_checkmate():
            return "ok"
    except Exception as ex:
        return f"error {ex}"
    return "wrong"


class Analyser:
    def __init__(self, args):
        self.engine = args.engine
        self.limit = chess.engine.Limit(
            nodes=args.nodes, depth=args.depth, time=args.time
        )
        self.hash = args.hash
        self.threads = args.threads
        self.syzygyPath = args.syzygyPath

    def analyze_fens(self, fens):
        result_fens = []
        engine = chess.engine.SimpleEngine.popen_uci(self.engine)
        if self.hash is not None:
            engine.configure({"Hash": self.hash})
        if self.threads is not None:
            engine.configure({"Threads": self.threads})
        if self.syzygyPath is not None:
            engine.configure({"SyzygyPath": self.syzygyPath})
        for fen, bm in fens:
            board = chess.Board(fen)
            info = engine.analyse(board, self.limit, game=board)
            m = info["score"].pov(board.turn).mate() if "score" in info else None
            pv = [m.uci() for m in info["pv"]] if "pv" in info else []
            result_fens.append((fen, bm, m, pv))

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
    parser.add_argument(
        "--nodes",
        type=str,
        help="nodes limit per position, default: 10**6 without other limits, otherwise None",
    )
    parser.add_argument("--depth", type=int, help="depth limit per position")
    parser.add_argument(
        "--time", type=float, help="time limit (in seconds) per position"
    )
    parser.add_argument("--hash", type=int, help="hash table size in MB")
    parser.add_argument(
        "--threads",
        type=int,
        help="number of threads per position (values > 1 may lead to non-deterministic results)",
    )
    parser.add_argument("--syzygyPath", help="path to syzygy EGTBs")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=cpu_count(),
        help="total number of threads script may use, default: cpu_count()",
    )
    parser.add_argument(
        "--epdFile",
        default="matetrack.epd",
        help="file containing the positions and their mate scores",
    )
    args = parser.parse_args()
    if args.nodes is None and args.depth is None and args.time is None:
        args.nodes = 10**6
    elif args.nodes is not None:
        args.nodes = eval(args.nodes)

    ana = Analyser(args)
    p = re.compile("([0-9a-zA-Z/\- ]*) bm #([0-9\-]*);")

    print("Loading FENs...")

    fens = []
    with open(args.epdFile) as f:
        for line in f:
            m = p.match(line)
            if not m:
                print("---------------------> IGNORING : ", line)
            else:
                fens.append((m.group(1), int(m.group(2))))

    print(f"{len(fens)} FENs loaded...")

    numfen = len(fens)
    workers = args.concurrency // (args.threads if args.threads else 1)
    assert (
        workers > 0
    ), f"Need concurrency >= threads, but concurrency = {args.concurrency} and threads = {args.threads}."
    fw_ratio = numfen // (4 * workers)
    fenschunked = list(chunks(fens, max(1, fw_ratio)))

    limits = [
        ("nodes", args.nodes),
        ("depth", args.depth),
        ("time", args.time),
        ("hash", args.hash),
        ("threads", args.threads),
        ("syzygyPath", args.syzygyPath),
    ]
    msg = (
        args.engine
        + " on "
        + args.epdFile
        + " with "
        + " ".join([f"--{k} {v}" for k, v in limits if v is not None])
    )

    print(f"\nMatetrack started for {msg} ...")

    res = []
    futures = []

    with tqdm(total=len(fenschunked), smoothing=0, miniters=1) as pbar:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as e:
            for entry in fenschunked:
                futures.append(e.submit(ana.analyze_fens, entry))

            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)
                res += future.result()

    print("")

    mates = bestmates = bettermates = wrongmates = fullpv = 0
    for fen, bestmate, mate, pv in res:
        if mate is not None:
            if mate * bestmate > 0:
                mates += 1
                if mate == bestmate:
                    bestmates += 1
                elif abs(mate) < abs(bestmate):
                    print(
                        f'Found mate #{mate} (better) for FEN "{fen}" with bm #{bestmate}.'
                    )
                    if pv:
                        print("PV:", " ".join(pv))
                    bettermates += 1
                pvstatus = pv_status(fen, mate, pv)
                if pvstatus == "ok":
                    fullpv += 1
                elif pvstatus != "short":
                    print(
                        f'Found mate #{mate} with PV status "{pvstatus}" for FEN "{fen}" with bm #{bestmate}.'
                    )
                    print("PV:", " ".join(pv))
            else:
                print(
                    f'Found mate #{mate} (wrong sign) for FEN "{fen}" with bm #{bestmate}.'
                )
                if pv:
                    print("PV:", " ".join(pv))
                wrongmates += 1

    print(f"\nUsing {msg}")
    print("Total fens:   ", numfen)
    print("Found mates:  ", mates)
    print("Best mates:   ", bestmates)
    if mates:
        print(f"Complete PVs:  {fullpv}/{mates} ({fullpv / mates * 100:.1f}%)")
    if bettermates:
        print("Better mates: ", bettermates)
    if wrongmates:
        print("Wrong mates:  ", wrongmates)

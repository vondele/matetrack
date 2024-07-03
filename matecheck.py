import argparse, random, re, sys, concurrent.futures, chess, chess.engine, chess.syzygy
from time import time
from multiprocessing import freeze_support, cpu_count
from tqdm import tqdm


class TB:
    def __init__(self, path):
        self.tb = chess.syzygy.Tablebase()
        sep = ";" if sys.platform.startswith("win") else ":"
        for d in path.split(sep):
            self.tb.add_directory(d)

    def probe(self, board):
        if (
            board.castling_rights
            or chess.popcount(board.occupied) > chess.syzygy.TBPIECES
        ):
            return None
        return self.tb.get_wdl(board)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def pv_status(fen, mate, score, pv, tb=None):
    # check if the given pv (list of uci moves) leads to checkmate #mate
    # if mate is None, check if pv leads to claimed TB win/loss
    losing_side = 1 if (mate and mate > 0) or (score and score > 0) else 0
    try:
        board = chess.Board(fen)
        for ply, move in enumerate(pv):
            if ply % 2 == losing_side and board.can_claim_draw():
                return "draw"
            # if EGTB is available, probe it to check PV correctness
            if tb is not None:
                wdl = tb.probe(board)
                if wdl is not None:
                    if abs(wdl) != 2:
                        return "draw"
                    if ply % 2 == losing_side and wdl != -2:
                        return "wrong"
                    if ply % 2 != losing_side and wdl != 2:
                        return "wrong"
            uci = chess.Move.from_uci(move)
            if not uci in board.legal_moves:
                raise Exception(f"illegal move {move} at position {board.epd()}")
            board.push(uci)
    except Exception as ex:
        return f'error "{ex}"'

    if mate:
        plies_to_checkmate = 2 * mate - 1 if mate > 0 else -2 * mate
        if len(pv) < plies_to_checkmate:
            return "short"
        if len(pv) > plies_to_checkmate:
            return "long"
        if board.is_checkmate():
            return "ok"
        return "wrong"

    # now check if the leaf node is in EGTB, with the correct result
    wdl = tb.probe(board)
    if wdl is None:
        return "short"
    if abs(wdl) != 2:
        return "draw"
    if (ply + 1) % 2 == losing_side and wdl != -2:
        return "wrong"
    if (ply + 1) % 2 != losing_side and wdl != 2:
        return "wrong"
    return "ok"


class Analyser:
    def __init__(self, args):
        self.engine = args.engine
        self.limit = chess.engine.Limit(
            nodes=args.nodes,
            depth=args.depth,
            time=args.time,
            mate=args.mate if args.mate else None,
        )
        self.mate = args.mate
        if self.mate is not None and self.mate == 0:
            self.nodes, self.depth, self.time = args.nodes, args.depth, args.time
        self.hash = args.hash
        self.threads = args.threads
        self.syzygyPath = args.syzygyPath
        self.minTBscore = args.minTBscore

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
            pvstatus = {}  #  stores (status, final_line)
            m, score, pvstr = None, None, ""
            nodes = depth = lastnodes = lasttime = 0
            if self.mate is not None and self.mate == 0:
                limit = chess.engine.Limit(
                    nodes=self.nodes, depth=self.depth, time=self.time, mate=abs(bm)
                )
            else:
                limit = self.limit
            lastnodes = 0
            lasttime = 0
            with engine.analysis(board, limit, game=board) as analysis:
                for info in analysis:
                    lastnodes = info.get("nodes", lastnodes)
                    lasttime = info.get("time", lasttime)
                    if "score" in info and not (
                        "upperbound" in info or "lowerbound" in info
                    ):
                        score = info["score"].pov(board.turn)
                        m = score.mate()
                        score = score.score()
                        if m is None and (
                            self.syzygyPath is None
                            or score is None
                            or abs(score) < self.minTBscore
                        ):
                            continue
                        pv = [m.uci() for m in info["pv"]] if "pv" in info else []
                        pvstr = " ".join(pv)
                        if (m, score, pvstr) not in pvstatus:
                            pvstatus[m, score, pvstr] = (
                                pv_status(fen, m, score, pv) if m else "None"
                            ), False
                        nodes = lastnodes
                        depth = info.get("depth", 0)
            if (m, score, pvstr) in pvstatus:  # mark final info line
                pvstatus[m, score, pvstr] = pvstatus[m, score, pvstr][0], True
            result_fens.append((fen, bm, pvstatus, nodes, depth, lastnodes, lasttime))

        engine.quit()

        return result_fens


if __name__ == "__main__":
    freeze_support()
    parser = argparse.ArgumentParser(
        description='Check how many (best) mates an engine finds in e.g. matetrack.epd, a file with lines of the form "FEN bm #X;".',
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
    parser.add_argument(
        "--mate",
        type=int,
        help="mate limit per position: a value of 0 will use bm #X as the limit, a positive value (in the absence of other limits) means only elegible positions will be analysed",
    )
    parser.add_argument("--hash", type=int, help="hash table size in MB")
    parser.add_argument(
        "--threads",
        type=int,
        help="number of threads per position (values > 1 may lead to non-deterministic results)",
    )
    parser.add_argument(
        "--syzygyPath",
        help="path(s) to syzygy EGTBs, with ':'/';' as separator on Linux/Windows",
    )
    parser.add_argument(
        "--minTBscore",
        type=int,
        help="lowest cp score for a TB win",
        default=20000 - 246,  # for SF this is TB_CP - MAX_PLY
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=cpu_count(),
        help="total number of threads script may use, default: cpu_count()",
    )
    parser.add_argument(
        "--epdFile",
        nargs="+",
        default=["matetrack.epd"],
        help="file(s) containing the positions and their mate scores",
    )
    parser.add_argument(
        "--showAllIssues",
        action="store_true",
        help="show all unique UCI info lines with an issue, by default show for each FEN only the first occurrence of each possible type of issue",
    )
    parser.add_argument(
        "--shortTBPVonly",
        action="store_true",
        help="for TB win scores, only consider short PVs an issue",
    )
    parser.add_argument(
        "--showAllStats",
        action="store_true",
        help="show nodes and depth statistics for best mates found (always True if --mate is supplied)",
    )
    parser.add_argument(
        "--bench",
        action="store_true",
        help="provide cumulative statistics for nodes searched and time used",
    )
    args = parser.parse_args()
    if (
        args.nodes is None
        and args.depth is None
        and args.time is None
        and args.mate is None
    ):
        args.nodes = 10**6
    elif args.nodes is not None:
        args.nodes = eval(args.nodes)

    ana = Analyser(args)
    p = re.compile("([0-9a-zA-Z/\- ]*) bm #([0-9\-]*);")

    unlimited = (
        args.mate and args.nodes is None and args.depth is None and args.time is None
    )

    fens = {}
    for epd in args.epdFile:
        with open(epd) as f:
            for line in f:
                m = p.match(line)
                if not m:
                    print("---------------------> IGNORING : ", line)
                else:
                    fen, bm = m.group(1), int(m.group(2))
                    if unlimited and args.mate < abs(bm):
                        continue  # avoid analyses that cannot terminate
                    if fen in fens:
                        bmold = fens[fen]
                        if bm != bmold:
                            print(
                                f'Warning: For duplicate FEN "{fen}" we only keep faster mate between #{bm} and #{bmold}.'
                            )
                            if abs(bm) < abs(bmold):
                                fens[fen] = bm
                    else:
                        fens[fen] = bm

    maxbm = max([abs(bm) for bm in fens.values()]) if fens else 0
    fens = list(fens.items())
    random.seed(42)
    random.shuffle(fens)  # try to balance the analysis time across chunks

    print(f"Loaded {len(fens)} FENs, with max(abs(bm)) = {maxbm}.")

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
        ("mate", args.mate),
        ("hash", args.hash),
        ("threads", args.threads),
        ("syzygyPath", args.syzygyPath),
    ]
    msg = (
        args.engine
        + " on "
        + " ".join(args.epdFile)
        + " with "
        + " ".join([f"--{k} {v}" for k, v in limits if v is not None])
    )

    print(f"\nMatetrack started for {msg} ...")
    engine = chess.engine.SimpleEngine.popen_uci(args.engine)
    name = engine.id.get("name", "")
    engine.quit()

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

    tb = TB(args.syzygyPath) if args.syzygyPath is not None else None
    if tb is not None:
        c = 0
        for _, _, pvstatus, _, _, _, _ in res:
            c += sum(1 for (_, score, _) in pvstatus if score is not None)
        if c:
            print(f"\nChecking {c} TB win PVs. This may take some time...")

    mates = bestmates = tbwins = 0
    issue = {
        "Better mates": [0, 0],
        "Wrong mates": [0, 0],
        "Bad PVs": [0, 0],
        "Wrong TB score": [0, 0],
    }
    bestnodes = [[] for _ in range(maxbm + 1)]
    bestdepth = [[] for _ in range(maxbm + 1)]
    for fen, bestmate, pvstatus, nodes, depth, _, _ in res:
        found_better = found_wrong = found_badpv = found_wrong_tb = False
        for (mate, score, pv), (status, last_line) in pvstatus.items():
            if mate:
                if mate * bestmate > 0:
                    if last_line:  #  for mate counts use last valid UCI info output
                        mates += 1
                        if mate == bestmate:
                            bestmates += 1
                            bestnodes[abs(mate)].append(nodes)
                            bestdepth[abs(mate)].append(depth)
                    if abs(mate) < abs(bestmate):
                        issue["Better mates"][0] += 1
                        if not found_better or args.showAllIssues:
                            issue["Better mates"][1] += int(not found_better)
                            found_better = True
                            print(
                                f'Found mate #{mate} (better) for FEN "{fen}" with bm #{bestmate}.'
                            )
                            print("PV:", pv)
                    if status != "ok":
                        issue["Bad PVs"][0] += 1
                        if not found_badpv or args.showAllIssues:
                            issue["Bad PVs"][1] += int(not found_badpv)
                            found_badpv = True
                            print(
                                f'Found mate #{mate} with PV status "{status}" for FEN "{fen}" with bm #{bestmate}.'
                            )
                            print("PV:", pv)
                else:
                    issue["Wrong mates"][0] += 1
                    if not found_wrong or args.showAllIssues:
                        issue["Wrong mates"][1] += int(not found_wrong)
                        found_wrong = True
                        print(
                            f'Found mate #{mate} (wrong sign) for FEN "{fen}" with bm #{bestmate}.'
                        )
                        print("PV:", pv)
            elif tb is not None:
                if score * bestmate > 0:
                    if last_line:
                        tbwins += 1
                    status = pv_status(fen, mate, score, pv.split(), tb)
                    if status != "ok" and not args.shortTBPVonly or status == "short":
                        issue["Bad PVs"][0] += 1
                        if not found_badpv or args.showAllIssues:
                            issue["Bad PVs"][1] += int(not found_badpv)
                            found_badpv = True
                            print(
                                f'Found TB score {score} with PV status "{status}" for FEN "{fen}" with bm #{bestmate}.'
                            )
                            print("PV:", pv)
                else:
                    issue["Wrong TB score"][0] += 1
                    if not found_wrong_tb or args.showAllIssues:
                        issue["Wrong TB score"][1] += int(not found_wrong_tb)
                        found_wrong_tb = True
                        print(
                            f'Found TB score {score} (wrong sign) for FEN "{fen}" with bm #{bestmate}.'
                        )
                        print("PV:", pv)

    print(f"\nUsing {msg}")
    if name:
        print("Engine ID:    ", name)
    print("Total FENs:   ", numfen)
    print("Found mates:  ", mates)
    print("Best mates:   ", bestmates)
    if tbwins:
        print("Found TB wins:", tbwins)

    if (args.showAllStats or args.mate is not None) and bestmates:
        print("\nBest mate statistics:")
        for bm in range(maxbm + 1):
            if bestnodes[bm]:
                nl, dl = bestnodes[bm], bestdepth[bm]
                print(
                    f"abs(bm) = {bm} - mates: {len(nl)}, nodes (min avg max): {min(nl)} {round(sum(nl)/len(nl))} {max(nl)}, depth (min avg max): {min(dl)} {round(sum(dl)/len(dl))} {max(dl)}"
                )
        nl = [n for l in bestnodes for n in l]
        dl = [d for l in bestdepth for d in l]
        print(
            f"All best mates: {len(nl)}, nodes (min avg max): {min(nl)} {round(sum(nl)/len(nl))} {max(nl)}, depth (min avg max): {min(dl)} {round(sum(dl)/len(dl))} {max(dl)}"
        )

    if sum([v[0] for v in issue.values()]):
        print(
            "\nParsing the engine's full UCI output, the following issues were detected:"
        )
        for key, value in issue.items():
            if value[0]:
                print(
                    f"{key}:{' ' * (14 - len(key))}{value[0]}   (from {value[1]} FENs)"
                )

    if args.bench:
        totalnodes = totaltime = 0
        for _, _, _, _, _, lastnodes, lasttime in res:
            totalnodes += lastnodes
            totaltime += lasttime
        print("\n===========================")
        print("Total time (ms) :", round(totaltime * 1000))
        print("Nodes searched  :", totalnodes)
        if totaltime > 0:
            print("Nodes/second    :", round(totalnodes / totaltime))

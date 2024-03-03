import argparse, chess, re


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Use PVs stored in .epd file to advance a number of plies. Can be used to change to-mate positions into to-be-mated positions, and vice-versa, in e.g. matetrackpv.epd.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--epdFile",
        default="matetrackpv.epd",
        help="file containing the positions, their mate scores and their PVs",
    )
    parser.add_argument(
        "--outFile",
        default="matedtrackpv.epd",
        help="output file with advanced positions, their mate scores and PVs",
    )
    parser.add_argument(
        "--plies",
        type=int,
        default=1,
        help="number of plies to advance",
    )
    parser.add_argument(
        "--targetMate",
        type=int,
        help="in each position advance enough plies to leave a mate-in-TARGETMATE (overrides --plies)",
    )
    parser.add_argument(
        "--mateType",
        choices=["all", "won", "lost"],
        default="all",
        help="type of positions to advance from",
    )
    args = parser.parse_args()

    p = re.compile("([0-9a-zA-Z/\- ]*) bm #([0-9\-]*);")
    fens = []

    with open(args.epdFile) as f:
        for line in f:
            m = p.match(line)
            assert m, f"error for line '{line[:-1]}' in file {args.epdFile}"
            fen, bm = m.group(1), int(m.group(2))
            _, _, pv = line.partition("; PV: ")
            pv, _, _ = pv[:-1].partition(";")  # remove '\n'
            pv = pv.split()
            fens.append((fen, bm, pv, line))

    print(f"{len(fens)} FENs loaded...")

    count, plies = 0, args.plies
    with open(args.outFile, "w") as f:
        for fen, bm, pv, line in fens:
            plies_to_checkmate = 2 * bm - 1 if bm > 0 else -2 * bm
            if args.targetMate:
                m = args.targetMate
                plies4m = 2 * m - 1 if m > 0 else -2 * m
                plies = plies_to_checkmate - plies4m
                if plies < 0:
                    plies = plies_to_checkmate + 1
            if (
                plies <= len(pv)
                and plies < plies_to_checkmate
                and (
                    args.mateType == "all"
                    or args.mateType == "won"
                    and bm > 0
                    or args.mateType == "lost"
                    and bm < 0
                )
            ):
                board = chess.Board(fen)
                for move in pv[:plies]:
                    board.push(chess.Move.from_uci(move))
                    bm = -bm + (1 if bm > 0 else 0)
                fen = board.epd()
                pv = pv[plies:]
                f.write(f"{fen} bm #{bm}; PV: {' '.join(pv)};\n")
                count += 1
            else:
                f.write(line)

    if args.targetMate:
        print(f"Number of #{args.targetMate} positions created: ", count)
    else:
        print(f"Positions in which we advanced {plies} plies: ", count)

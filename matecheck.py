import re
import argparse
import concurrent.futures
import chess.engine
import chess
from multiprocessing import freeze_support

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
        for input in fens:
            board = chess.Board(input[0])
            info = engine.analyse(board, chess.engine.Limit(nodes=self.nodes))
            if "score" in info:
                result_fens.append(
                    [input[0], input[1], info["score"].pov(board.turn).mate()]
                )
            else:
                result_fens.append([input[0], input[1], None])

        engine.quit()

        return result_fens

if __name__ == "__main__":
    freeze_support()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stockfish", type=str, default="./stockfish", help="Name of the stockfish binary"
    )
    parser.add_argument("--nodes", type=int, default=1000000, help="nodes per pos")
    args = parser.parse_args()

    ana = Analyser(args.stockfish, args.nodes)

    p = re.compile("([0-8a-zA-Z/\- ]*) bm #([0-9\-]*);")
    fens = []
    
    print("Loading FENs...")

    with open(
        "ChestUCI_23102018.epd", "r", encoding="utf-8-sig", errors="surrogateescape"
    ) as f:
        for line in f:
            m = p.match(line)
            if not m:
                print("---------------------> IGNORING : ", line)
            else:
                fens.append([m.group(1), int(m.group(2))])
    
    print("FENs loaded...")
    print("Mate track started...")
    
    numfen = len(fens)
    fenschunked = list(chunks(fens, 10))
    res = []
    count = 0;
    if True:
        with concurrent.futures.ProcessPoolExecutor() as e:
            results = e.map(ana.analyze_fens, fenschunked)
            for r in results:
                count += 10
                print("\rProgress: %d%%" % (count * 100 / numfen), end="")
                res = res + r
        print("\n")
        
    mates = 0
    bestmates = 0
    bettermates = 0
    for r in res:
        if not r[2]:
            continue
        mates = mates + 1
        if abs(r[1]) == abs(r[2]):
            bestmates = bestmates + 1

    print("Using %s with %d nodes" % (args.stockfish, args.nodes))
    print("Total fens:   ", numfen)
    print("Found mates:  ", mates)
    print("Best mates:   ", bestmates)

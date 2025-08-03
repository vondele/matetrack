import nevergrad as ng

import sys
import subprocess
import json
import argparse

from mpi4py import MPI
from mpi4py.futures import MPIPoolExecutor
from multiprocessing import freeze_support, cpu_count


def get_sf_parameters(stockfish_exe):
    """Run sf to obtain the tunable parameters"""

    process = subprocess.Popen(
        stockfish_exe, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    output = process.communicate(input=b"quit\n")[0]
    if process.returncode != 0:
        sys.stderr.write("get_sf_parameters: failed to execute command: %s\n" % command)
        sys.exit(1)

    # parse for parameter output
    params = ng.p.Dict()
    for line in output.decode("utf-8").split("\n"):
        if "Stockfish" in line or not "," in line:
            continue
        fields = line.split(",")
        params[fields[0]] = ng.p.Scalar(
            init=int(fields[1]), lower=int(fields[2]), upper=int(fields[3])
        ).set_integer_casting()

    return params


class Matetrack:
    def __init__(self, engine, nodes, concurrency, epdFile):
        self.engine = engine
        self.nodes = nodes
        self.concurrency = concurrency
        self.epdFile = epdFile

    def call(self, d):
        cmd = [
            "python",
            "matecheck.py",
            "--engine",
            self.engine,
            "--epdFile",
            self.epdFile,
            "--nodes",
            str(self.nodes),
            "--concurrency",
            str(self.concurrency),
            "--engineOpts",
            json.dumps(d),
        ]
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if output.returncode != 0:
            print("Executing matecheck failed....")
            print(cmd)
            print("yields: ")
            print(output.stderr)
            print("after: ")
            print(output.stdout)
            sys.exit(1)

        for line in output.stdout.split("\n"):
            # we minimize, so return minus the number of best mates
            if "Best mates:  " in line:
                return -int(line.split()[2])
        # on error...
        sys.exit(1)
        return 1


def ng4mt(engine, nodes, concurrency, epdFile, ngBudget):
    mpi_size = MPI.COMM_WORLD.Get_size()
    print("MPI Size: ", mpi_size, flush=True)

    # define optimizer param space
    param = get_sf_parameters(engine)

    print("Number of params: ", len(param))

    optimizer = ng.optimizers.NgIoh7(
        parametrization=param, budget=ngBudget, num_workers=mpi_size - 1
    )

    matetrack = Matetrack(engine, nodes, concurrency, epdFile)

    with MPIPoolExecutor(max_workers=optimizer.num_workers) as executor:
        recommendation = optimizer.minimize(
            matetrack.call, executor=executor, batch_mode=False, verbosity=2
        )  # best value

    print("Final recommendation: ", json.dumps(recommendation.value))
    print("Re-evaluated at recommendation: ", matetrack.call(recommendation.value))


if __name__ == "__main__":
    freeze_support()
    parser = argparse.ArgumentParser(
        description="optimize for mate",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--engine",
        default="./stockfish",
        help="name of the engine binary",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=1000000,
        help="nodes limit per position, default: 1000000",
    )
    parser.add_argument(
        "--ngBudget",
        type=int,
        default=500,
        help="Budget for nevergrad to call matecheck",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=cpu_count(),
        help="total number of threads script may use, default: cpu_count()",
    )
    parser.add_argument(
        "--epdFile",
        type=str,
        default="matetrack.epd",
        help="file(s) containing the positions and their mate scores",
    )

    args = parser.parse_args()

    ng4mt(args.engine, args.nodes, args.concurrency, args.epdFile, args.ngBudget)

import argparse
import json
import os
import subprocess
import sys


def shas_from_csvs(csvFiles):
    shas = set()
    for csvFile in csvFiles:
        with open(csvFile) as f:
            for line in f:
                line = line.strip()
                if line.startswith("Commit") or not line:  # ignore the header
                    continue
                parts = line.split(",")
                if len(parts) >= 2 and len(parts[1]) == 40:
                    shas.add(parts[1])
    return shas


def subjects_from_clone(shas, sfDir):
    out = subprocess.run(
        ["git", "-C", sfDir, "log", "--all", "--format=%H%x1f%s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    subjects = {}
    for line in out.splitlines():
        sha, _, subject = line.partition("\x1f")
        if sha in shas:
            subjects[sha] = subject
    return subjects


def main():
    parser = argparse.ArgumentParser(
        description="Update commitsubjects.json, the SHA -> commit subject "
        "mapping used by the interactive graphs in web/, by backfilling the "
        "subjects of all SHAs found in the csv files from a local clone of "
        "the Stockfish repository. Exits with a nonzero status if a SHA has "
        "no subject in the clone.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--csvFile",
        nargs="+",
        default=["matetrack1000000.csv", "classic1000000.csv"],
        help="file(s) with the SHAs to cover",
    )
    parser.add_argument(
        "--sfDir", default="Stockfish", help="directory of the Stockfish clone"
    )
    parser.add_argument(
        "--output", default="commitsubjects.json", help="json file to write"
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="git fetch the Stockfish clone before reading the subjects",
    )
    args = parser.parse_args()

    if args.fetch:
        subprocess.run(["git", "-C", args.sfDir, "fetch", "origin"], check=True)

    shas = shas_from_csvs(args.csvFile)
    try:
        subjects = subjects_from_clone(shas, args.sfDir)
    except FileNotFoundError:
        sys.exit(f"ERROR: no git repository at '{args.sfDir}', clone Stockfish first")
    except subprocess.CalledProcessError as e:
        sys.exit(f"ERROR: git log failed: {e.stderr.strip()}")

    if os.path.exists(args.output):
        with open(args.output) as f:
            existing = json.load(f)
    else:
        existing = {}

    merged = dict(existing)
    merged.update(subjects)
    added = sum(1 for sha in shas if sha in subjects and sha not in existing)
    missing = sorted(sha for sha in shas if sha not in merged)

    with open(args.output, "w") as f:
        json.dump(dict(sorted(merged.items())), f, indent=1)
        f.write("\n")

    print(
        f"{args.output}: {len(merged)} entries, {added} added, "
        f"{len(missing)} missing for the {len(shas)} SHAs in the csv files"
    )
    if missing:
        for sha in missing[:10]:
            print(f"  no subject for {sha}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
        sys.exit(1)


if __name__ == "__main__":
    main()

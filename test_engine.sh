#!/bin/bash

ENGINE=./stockfish
EPD=matetrack.epd
THREADS=1
ITERATIONS=6

# Parse command line options
while [[ "$#" -gt 0 ]]; do
    case $1 in
    --engine)
        ENGINE="$2"
        shift
        ;;
    --epdFile)
        EPD="$2"
        shift
        ;;
    --threads)
        THREADS="$2"
        shift
        ;;
    --iterations)
        ITERATIONS="$2"
        shift
        ;;
    --help)
        echo "Usage: $0 --engine <engine> --epdFile <epdFile> --threads <threads> --iterations <iterations>"
        echo ""
        echo "Options:"
        echo "  --engine      parameter passed to matecheck.py (default: ./stockfish)"
        echo "  --epdFile     parameter passed to matecheck.py (default: matetrack.epd)"
        echo "  --threads     parameter passed to matecheck.py (default: 1)"
        echo "  --iterations  maximal power of 10 to use for --nodes (default: 6)"
        echo ""
        echo "The script checks if an engine reports correct mate scores from aborted searches."
        echo "Transient(!) 'better' mates reported by an engine may indicate a bug."
        echo "However, a lack of such mates being reported is not a guarantee that the engine handles all mate scores correctly."
        exit 0
        ;;
    *)
        echo "Unknown parameter passed: $1"
        exit 1
        ;;
    esac
    shift
done

EPD=${EPD%.epd}

echo "Running $ENGINE on ${EPD}.epd with --threads $THREADS"

for p in $(seq 1 $ITERATIONS); do
    nodes=$((10 ** p))
    out="${ENGINE}_${EPD}_threads${THREADS}_nodes1e${p}.log"
    python matecheck.py --epdFile "${EPD}.epd" --engine "$ENGINE" --nodes "$nodes" --threads "$THREADS" >&"$out"
    echo "--nodes $nodes done, output saved to $out"
    grep "\(better\|wrong\|PV:\)" "$out"
done

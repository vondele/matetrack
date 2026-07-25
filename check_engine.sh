#!/bin/bash

# exit on errors
set -euo pipefail

RED='\033[1;31m'
GREEN='\033[1;32m'
BOLD='\033[1m'
NOCOL='\033[0m'

DEFAULT_ENGINE="./stockfish"
DEFAULT_SYZYGY_PATH=""
DEFAULT_NODES="100000"
DEFAULT_GOMATENODES="100000000"
DEFAULT_TIME="3"
DEFAULT_TIMEINC="0.01"
DEFAULT_CONCURRENCY=$(nproc)
DEFAULT_MAXTBSCORE="20000"
DEFAULT_MINTBSCORE="19754"
DEFAULT_MAXVALIDMATE="123"
DEFAULT_MINVALIDMATE="-123"
ENGINE=$DEFAULT_ENGINE
SYZYGY_PATH=$DEFAULT_SYZYGY_PATH
NODES=$DEFAULT_NODES
GOMATENODES=$DEFAULT_GOMATENODES
TIME=$DEFAULT_TIME
TIMEINC=$DEFAULT_TIMEINC
CONCURRENCY=$DEFAULT_CONCURRENCY
SHORTTBPVONLY=""
MAXTBSCORE=$DEFAULT_MAXTBSCORE
MINTBSCORE=$DEFAULT_MINTBSCORE
MAXVALIDMATE=$DEFAULT_MAXVALIDMATE
MINVALIDMATE=$DEFAULT_MINVALIDMATE

FAILS=0

while [[ "$#" -gt 0 ]]; do
  case $1 in
  -e | --engine)
    ENGINE="$2"
    shift
    ;;
  --syzygyPath)
    SYZYGY_PATH="$2"
    shift
    ;;
  --nodes)
    NODES="$2"
    shift
    ;;
  --goMateNodes)
    GOMATENODES="$2"
    shift
    ;;
  --time)
    TIME="$2"
    shift
    ;;
  --timeinc)
    TIMEINC="$2"
    shift
    ;;
  -c | --concurrency)
    CONCURRENCY="$2"
    shift
    ;;
  --shortTBPVonly)
    SHORTTBPVONLY="true"
    ;;
  --maxTBscore)
    MAXTBSCORE="$2"
    shift
    ;;
  --minTBscore)
    MINTBSCORE="$2"
    shift
    ;;
  --maxValidMate)
    MAXVALIDMATE="$2"
    shift
    ;;
  --minValidMate)
    MINVALIDMATE="$2"
    shift
    ;;
  -h | --help)
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -e, --engine <path>       Path to the engine binary (default: $DEFAULT_ENGINE)"
    echo "  --syzygyPath <path>       Path(s) to the syzygy EGTBs (default: none)"
    echo "  --nodes <value>           Number of nodes per position for standard tests (default: $DEFAULT_NODES)"
    echo "  --goMateNodes <value>     Number of nodes per position for |bm| <= 2 go-mate tests (default: $DEFAULT_GOMATENODES)"
    echo "  --time <value>            Number of seconds per position for gameplay tests (default: $DEFAULT_TIME)"
    echo "  --timeinc <value>         Time increment (in seconds) for gameplay tests (default: $DEFAULT_TIMEINC)"
    echo "  -c, --concurrency <value> Total number of threads script may use (default: $DEFAULT_CONCURRENCY)"
    echo "  --shortTBPVonly           Parameter passed to matecheck.py"
    echo "  --maxTBscore <value>      Parameter passed to matecheck.py (default: $DEFAULT_MAXTBSCORE)"
    echo "  --minTBscore <value>      Parameter passed to matecheck.py (default: $DEFAULT_MINTBSCORE)"
    echo "  --maxValidMate <value>    Parameter passed to matecheck.py (default: $DEFAULT_MAXVALIDMATE)"
    echo "  --minValidMate <value>    Parameter passed to matecheck.py (default: $DEFAULT_MINVALIDMATE)"
    exit 0
    ;;
  *)
    echo "Unknown parameter passed: $1"
    exit 1
    ;;
  esac
  shift
done

if [ ! -f "$ENGINE" ]; then
  echo "ERROR: Cannot find engine binary '$ENGINE'."
  exit 1
elif [ ! -x "$ENGINE" ]; then
  echo "ERROR: Engine binary '$ENGINE' is not executable."
  exit 1
fi

if [ "$CONCURRENCY" -lt "4" ]; then
  echo "ERROR: Concurrency must be at least 4."
  exit 1
fi

UCI=$(printf "uci\nquit" | "$ENGINE")

SCORES="mate"
FLAG_ARGS=()
if [ -n "$SYZYGY_PATH" ]; then
  SCORES="mate/TB"
  if [ -n "$SHORTTBPVONLY" ]; then
    FLAG_ARGS=("--shortTBPVonly")
  fi
fi

echo "Checking $ENGINE for correct $SCORES scores and complete PVs..."

# Explicitly state unseen CLI option changes (the remainder can be seen from output)
CLI_CHANGES="${FLAG_ARGS[@]}"
if [ "$MAXTBSCORE" -ne "$DEFAULT_MAXTBSCORE" ]; then
  CLI_CHANGES=$CLI_CHANGES" --maxTBscore $MAXTBSCORE"
fi
if [ "$MINTBSCORE" -ne "$DEFAULT_MINTBSCORE" ]; then
  CLI_CHANGES=$CLI_CHANGES" --minTBscore $MINTBSCORE"
fi
if [ "$MAXVALIDMATE" -ne "$DEFAULT_MAXVALIDMATE" ]; then
  CLI_CHANGES=$CLI_CHANGES" --maxValidMate $MAXVALIDMATE"
fi
if [ "$MINVALIDMATE" -ne "$DEFAULT_MINVALIDMATE" ]; then
  CLI_CHANGES=$CLI_CHANGES" --minValidMate $MINVALIDMATE"
fi
if [ -n "$CLI_CHANGES" ]; then
  echo "Running with the non-default option(s) $CLI_CHANGES"
fi

run_test() {
  local name="$1"
  local output_file="$2"
  shift 2
  echo -e "\n${BOLD}--- Running: $name ---$NOCOL"

  python matecheck.py --concurrency "$CONCURRENCY" --maxTBscore "$MAXTBSCORE" --minTBscore "$MINTBSCORE" --maxValidMate "$MAXVALIDMATE" --minValidMate "$MINVALIDMATE" "$@" | tee "$output_file"

  if grep -q "issues were detected" "$output_file"; then
    echo -e "${RED}ERROR: Issues detected in $name.$NOCOL Check $output_file."
    FAILS=$((FAILS + 1))
  fi
}

run_suite() {
  local egtb="$1"
  suffix=".out"
  SYZYGY_ARGS=()
  if [ -n "$egtb" ]; then
    SYZYGY_ARGS=("--syzygyPath" "$egtb")
    suffix=".egtb.out"
    egtb=" w/ EGTBs"
  fi

  for th in 1 4; do
    run_test "th$th standard$egtb" "matecheck$th$suffix" "${SYZYGY_ARGS[@]}" "${FLAG_ARGS[@]}" --engine "$ENGINE" --epdFile mates2000.epd --nodes "$NODES" --threads "$th"

    # In gameplay PVs for TB wins/losses are usually unreliable within the EGTB.
    run_test "th$th gameplay$egtb" "matecheck${th}g$suffix" "${SYZYGY_ARGS[@]}" "${FLAG_ARGS[@]}" --shortTBPVonly --engine "$ENGINE" --epdFile mates2000.epd --time "$TIME" --timeinc "$TIMEINC" --threads "$th"

    if [ "$GOMATENODES" -eq "0" ]; then
      echo -e "\n${BOLD}--- Skipping: th$th go-mate$egtb ---$NOCOL"
    else
      run_test "th$th go-mate$egtb" "matecheck${th}gm$suffix" "${SYZYGY_ARGS[@]}" "${FLAG_ARGS[@]}" --engine "$ENGINE" --epdFile matetrack.epd matedtrack.epd --bmMax 2 --mate 0 --nodes "$GOMATENODES" --threads "$th"

      total=$(grep "Total FENs:" "matecheck${th}gm$suffix" | awk '{print $3}')
      bmates=$(grep "Best mates:" "matecheck${th}gm$suffix" | awk '{print $3}')

      if [ "$bmates" -ne "$total" ]; then
        echo -e "${RED}ERROR: At least one go-mate search did not yield the expected mate within $GOMATENODES nodes. (Expected: $total, Found: $bmates)$NOCOL"
        FAILS=$((FAILS + 1))
      fi
    fi

    if ! echo "$UCI" | grep -q "MultiPV"; then
      echo -e "\n${RED}WARNING: Engine does not support UCI option MultiPV. Skipping th$th multiPV$egtb.$NOCOL"
    else
      run_test "th$th multiPV$egtb" "matecheck${th}mpv$suffix" "${SYZYGY_ARGS[@]}" "${FLAG_ARGS[@]}" --engine "$ENGINE" --epdFile mates2000.epd --nodes "$NODES" --multiPV 4 --multipvFile matetrack_multipv.epd matedtrack_multipv.epd --threads "$th"
    fi
  done
}

run_suite ""

if [ -n "$SYZYGY_PATH" ]; then
  if ! echo "$UCI" | grep -q "SyzygyPath"; then
    echo -e "\n${RED}WARNING: Engine does not support UCI option SyzygyPath. Skipping EGTB tests.$NOCOL"
  else
    run_suite "$SYZYGY_PATH"

    if ! echo "$UCI" | grep -q "Syzygy50MoveRule"; then
      echo -e "\n${RED}WARNING: Engine does not support UCI option Syzygy50MoveRule. Skipping cursed tests.$NOCOL"
    else
      grep 5men cursed.epd >cursed5.epd

      for th in 1 4; do
        run_test "th$th --syzygy50MoveRule false" "matecheckcursed${th}.egtb.out" --syzygyPath "$SYZYGY_PATH" "${FLAG_ARGS[@]}" --engine "$ENGINE" --epdFile cursed5.epd --nodes "$NODES" --threads "$th" --syzygy50MoveRule false

        mates=$(grep "Found mates:" "matecheckcursed${th}.egtb.out" | awk '{print $3}')
        tbwins=$(grep "Found TB wins:" "matecheckcursed${th}.egtb.out" | awk '{print $4}')

        if [ $(($mates + $tbwins)) -ne 32 ]; then
          echo -e "${RED}ERROR: Sum of mates and TB wins is not 32 in matecheckcursed${th}.egtb.out.$NOCOL"
          FAILS=$((FAILS + 1))
        fi
      done
    fi
  fi
fi

echo -e "\n====================================="
if [ "$FAILS" -eq 0 ]; then
  echo -e "===${GREEN} ALL TESTS PASSED SUCCESSFULLY ${NOCOL}==="
  echo -e "====================================="
  exit 0
else
  echo -e "===${RED}  FINISHED WITH $FAILS FAILURE(S)   ${NOCOL}==="
  echo -e "====================================="
  exit 1
fi

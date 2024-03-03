#  Track the evolution of Stockfish mate finding effectiveness 

Track the performance of [official Stockfish](https://github.com/official-stockfish/Stockfish)
in finding the (best) mates within the 6558 mate problems in [`matetrack.epd`](matetrack.epd).
The raw data is available in [`matetrack1000000.csv`](matetrack1000000.csv),
and is visualized in the graphs below.

<p align="center">
  <img src="matetrack1000000all.png?raw=true">
</p>

<p align="center">
  <img src="matetrack1000000.png?raw=true">
</p>

---

### List of available test suites

* `ChestUCI_23102018.epd`: the original suite derived from publicly available `ChestUCI.epd` files, see [FishCooking](https://groups.google.com/g/fishcooking/c/lh1jTS4U9LU/m/zrvoYQZUCQAJ). It contains 6561 positions, with one draw, two positions that are likely draws due to the 50 move rule, some illegal positions and some positions with a sub-optimal value for the fastest known mate.
* **`matetrack.epd`**: The successor to `ChestUCI_23102018.epd`, with all illegal positions removed and all known errors corrected. The plots shown above are based on this file. It contains 6558 mate problems, ranging from mate in 1 (#1) to #126 for positions with between 4 and 32 pieces. In 26 positions the side to move is going to get mated.
* `matetrackpv.epd`: The same as `matetrack.epd`, but for each position the file also includes a PV leading to the checkmate, if such a PV is known.
* `matedtrack.epd`: Derived from `matetrackpv.epd` by applying a best move in all those positions, where the winning side is to move, and where a best move is known. The order of the positions in `matedtrack.epd` corresponds 1:1 to the order in `matetrack.epd`. So the new test suite still contains 6558 mate problems, but for 6506 of them the side to move is going to get mated.

### Automatic creation of new test positions

With the help of the script `advancepvs.py` it is easy to derive new mate
puzzles from the information stored in `matetrackpv.epd`. For example, the file `matedtrack.epd` has been created with the command
```shell
python advancepvs.py --plies 1 --mateType won && sed 's/; PV.*/;/' matedtrackpv.epd > matedtrack.epd
```
Similarly, a file with only `#-10` positions can be created with the command
```shell
python advancepvs.py --targetMate -10 && grep 'bm #-10;' matedtrackpv.epd > mate-10.epd
```

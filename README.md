#  Track the evolution of Stockfish mate finding effectiveness 

Track the performance of [official Stockfish](https://github.com/official-stockfish/Stockfish)
in finding the (best) mates within the 6560 mate problems in [`matetrack.epd`](matetrack.epd).

The raw data is available in [`matetrack1000000.csv`](matetrack1000000.csv),
and visualized in the graphs below.

<p align="center">
  <img src="matetrack1000000all.png?raw=true">
</p>

<p align="center">
  <img src="matetrack1000000.png?raw=true">
</p>

---

### List of available test suites

* `ChestUCI_23102018.epd`: the original suite derived from publicly available
`ChestUCI.epd` files, see
[FishCooking](https://groups.google.com/g/fishcooking/c/lh1jTS4U9LU/m/zrvoYQZUCQAJ). It contains 6561 positions, with some wrongly classified
mates, one draw and some illegal positions.
* **`matetrack.epd`**: The successor to `ChestUCI_23102018.epd`, with all illegal positions removed and all known errors corrected. The plots shown above are based on this file. It contains 6560 mate problems, ranging from mate in 1 (#1) to #126 for positions with between 4 and 32 pieces. In 26 positions the side to move is going to get mated.
* `matedtrack.epd`: Derived from `matetrack.epd` by applying a best move in all those positions, where the winning side is to move, and where a best move is known. The order of the positions in `matedtrack.epd` corresponds 1:1 to the order in `matetrack.epd`. So the new test suite still contains 6560 mate problems,
but for 6404 of them the side to move is going to get mated.

#!/bin/bash

# exit on errors
set -e

echo "started at: " `date`

# use 1M nodes for each position
nodes=1000000

# clone SF as needed, download an old, non-embedded master net as well
if [[ ! -e Stockfish ]]; then
   git clone https://github.com/official-stockfish/Stockfish.git
   wget https://tests.stockfishchess.org/api/nn/nn-82215d0fd0df.nnue
fi

# update SF and get sorted revision list (exclude non-compiling commits)
cd Stockfish/src
git checkout master >& checkout.log
git fetch origin  >& fetch.log
git pull >& pull.log
revs=`git rev-list --reverse dd9cf305816c84c2acfa11cae09a31c4d77cc5a5^..HEAD |\
      grep -v 44c320a572188b5875291103edb344c584b91d19 |\
      grep -v bdeda52efd55c97d0f5da908267c01f973371e5d |\
      grep -v fbb2ffacfdf10fc37d8ee2d2093b2cec629f6067 |\
      grep -v 7f4de0196b8169e3d0deef75bfcfff6d10166d99 |\
      grep -v cddc8d4546ab0d7b63081cb75cbca66b9c68628b |\
      grep -v 4a7b8180ecaef7d164fa53a1d545372df1173596`
cd ../..

csv=matetrack$nodes.csv  # list of previously computed results
new=new$nodes.csv        # temporary list of newly computed results
out=out.tmp              # file for output from matecheck.py

# if necessary, create a new csv file with the correct header
if [[ ! -f $csv ]]; then
   echo "Commit Date,Commit SHA,Number of positions,Number of mates,Number of best mates" > $csv
fi

# if necessary, merge results from a previous (interrupted) run of this script
if [[ -f $new ]]; then
   cat $new >> $csv && rm $new
   python3 plotdata.py $csv
fi

# go over the revision list and compute missing results if necessary
for rev in $revs
do
   if ! grep -q "$rev" "$csv"; then
      echo "running matecheck on revision $rev "
      # compile revision and get binary
      cd Stockfish/src
      git checkout $rev >& checkout2.log
      epoch=`git show --pretty=fuller --date=iso-strict $rev | grep 'CommitDate' | awk '{print $NF}'`
      make clean >& clean.log
      CXXFLAGS='-march=native' make -j ARCH=x86-64-avx2 profile-build >& make.log
      mv stockfish ../..
      cd ../..

      # run a matecheck round on this binary
      python3 matecheck.py --stockfish ./stockfish --nodes $nodes >& $out

      # collect results for this revision
      total=`grep "Total fens:" $out | awk '{print $NF}'`
      mates=`grep "Found mates:" $out | awk '{print $NF}'`
      bmates=`grep "Best mates:" $out | awk '{print $NF}'`
      echo "$epoch,$rev,$total,$mates,$bmates" >> $new
   fi
done

if [[ -f $new ]]; then
   cat $new >> $csv && rm $new
   python3 plotdata.py $csv
fi

git add $csv matetrack$nodes.png matetrack"$nodes"all.png
git diff --staged --quiet || git commit -m "Update results"
git push origin master >& push.log

echo "ended at: " `date`

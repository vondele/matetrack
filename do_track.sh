#!/bin/bash

# exit on errors
set -e

echo "started at: " `date`

# use 1M nodes for each position
nodes=1000000

# clone SF as needed, download an old, non-embedded master net as well.
if [[ ! -e Stockfish ]]; then
   git clone https://github.com/official-stockfish/Stockfish.git
   wget https://tests.stockfishchess.org/api/nn/nn-82215d0fd0df.nnue
fi

# update SF and get revision list (exclude non-compiling commits)
cd Stockfish/src
git checkout master >& checkout.log
git fetch origin  >& fetch.log
git pull >& pull.log
revs=`git rev-list dd9cf305816c84c2acfa11cae09a31c4d77cc5a5^..HEAD |\
      grep -v 44c320a572188b5875291103edb344c584b91d19 |\
      grep -v bdeda52efd55c97d0f5da908267c01f973371e5d |\
      grep -v fbb2ffacfdf10fc37d8ee2d2093b2cec629f6067 |\
      grep -v 7f4de0196b8169e3d0deef75bfcfff6d10166d99 |\
      grep -v cddc8d4546ab0d7b63081cb75cbca66b9c68628b |\
      grep -v 4a7b8180ecaef7d164fa53a1d545372df1173596`
cd ../..

# go over the revision list and see if we have mate results already
for rev in $revs
do
   file=out.$rev.$nodes
   if [[ ! -f $file ]]; then
      echo "generate $file "
      # compile revision and get binary
      cd Stockfish/src
      git checkout $rev >& checkout2.log
      epoch=`git show --pretty=fuller --date=short $rev | grep 'CommitDate' | awk '{print $NF}'`
      make clean >& clean.log
      make -j ARCH=x86-64-modern profile-build >& make.log
      mv stockfish ../..
      cd ../..

      # run a matecheck round on this binary
      python3 matecheck.py --stockfish ./stockfish --nodes $nodes >& out.tmp
      mv out.tmp $file

      # collect results for this revision
      mates=`grep Best $file | awk '{print $NF}'`
      echo "$rev $epoch $mates" >> all_results.txt

      # update the graph
      awk '{print $2,$3}' all_results.txt | sort  | xmgrace  -param matefinding.xmgrparams - -printfile all_results.png -hdevice PNG -hardcopy
      awk '{print $2,$3}' all_results.txt | sort | tail -n 50  | xmgrace  -param matefinding.xmgrparams - -printfile all_results_recent.png -hdevice PNG -hardcopy
   fi
done

git add all_results.txt all_results.png all_results_recent.png
git diff --staged --quiet || git commit -m "Update results"
git push origin master

echo "ended at: " `date`

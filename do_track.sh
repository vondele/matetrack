#!/bin/bash

# exit on errors
set -e

# use 1M nodes for each position
nodes=1000000

# clone SF as needed, download an old, non-embedded master net as well.
if [[ ! -e Stockfish ]]; then
   git clone https://github.com/official-stockfish/Stockfish.git
   wget https://tests.stockfishchess.org/api/nn/nn-82215d0fd0df.nnue
fi

# update SF and get revision list
cd Stockfish/src
git checkout master >& checkout.log
git fetch origin  >& fetch.log
git pull >& pull.log
revs=`git rev-list dd9cf305816c84c2acfa11cae09a31c4d77cc5a5^..HEAD`
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
   fi
done

git add all_results.txt all_results.png
git commit -m "Update results"
git push origin master

#!/bin/bash
#
# Script to convert old out.sha.nodes files into csv format. 
# (Can be removed from repo once transition of all existing commits is done.)

# exit on errors
set -e

# use 1M nodes for each position
nodes=1000000

# clone SF as needed
if [[ ! -e Stockfish ]]; then
   git clone https://github.com/official-stockfish/Stockfish.git
fi

# update SF and get revision list (exclude non-compiling commits)
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
tags=`git ls-remote --quiet --tags | grep -E "sf_[0-9]+(\.[0-9]+)?"`
cd ../..

csv=matetrack$nodes.csv
new=new.csv
if [[ ! -f $csv ]]; then
  echo "Commit Date,Commit SHA,Number of positions,Number of mates,Number of best mates,Release tag" > $csv
fi
if [[ -f $new ]]; then
  rm $new
fi

# go over the revision list and see if we have mate results already
for rev in $revs
do
  if ! grep -q "$rev" "$csv"; then
    file=outs/out.$rev.$nodes
    if [[ ! -f $file ]]; then
       echo "Output file $file is missing."
    else
       cd Stockfish/src
       git checkout $rev >& checkout2.log
       epoch=`git show --pretty=fuller --date=iso-strict $rev | grep 'CommitDate' | awk '{print $NF}'`
       tag=`echo "$tags" | grep $rev | sed 's/.*\///'`
       cd ../..

       # collect results for this revision
       total=`grep "Total fens:" $file | awk '{print $NF}'`
       mates=`grep "Found mates:" $file | awk '{print $NF}'`
       bmates=`grep "Best mates:" $file | awk '{print $NF}'`
       echo "$epoch,$rev,$total,$mates,$bmates,$tag" >> $new
    fi
  fi
done

if [[ -f $new ]]; then
  cat $new >> $csv && rm $new
fi

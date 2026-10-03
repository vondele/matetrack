#!/bin/bash

# serve a local preview of the web site at http://localhost:8000

# exit on errors
set -e
cd "$(dirname "$0")"

# copy the data files the site loads from web/data (as the workflow does)
mkdir -p data
cp ../matetrack1000000.csv ../classic1000000.csv ../commitsubjects.json data/

echo "serving web/ at http://localhost:8000 - press Ctrl+C to stop"
python3 -m http.server 8000

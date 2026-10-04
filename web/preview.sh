#!/bin/bash

# serve a local preview of the web site at http://localhost:PORT (default 8000)

# exit on errors
set -e
cd "$(dirname "$0")"

# copy the data files the site loads from web/data (as the workflow does)
mkdir -p data
cp ../matetrack1000000.csv ../classic1000000.csv ../commitsubjects.json data/

# use the given port, or the first free one starting from 8000, so that a
# server still running elsewhere does not block the preview
port=${1:-8000}
while ! python3 -c "import socket; socket.socket().bind(('', $port))" 2>/dev/null; do
  port=$((port + 1))
done

echo "serving web/ at http://localhost:$port - press Ctrl+C to stop"
python3 -m http.server "$port"

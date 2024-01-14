format:
	black --quiet matecheck.py plotdata.py
	shfmt -w -i 4 do_track.sh test_engine.sh

all: format

#!/usr/bin/env sh
set -eu
python -m pytest -q
python -m compileall -q backend risk signals

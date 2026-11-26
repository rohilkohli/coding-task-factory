#!/bin/bash
# Reference solution: restore the upstream implementation of click.DateTime
# (pallets/click @ 08b803cf32ceb2ae6a772c62d5da42757a897d44).
set -euo pipefail
cp /solution/files/src/click/types.py /app/src/click/types.py
cp /solution/files/src/click/__init__.py /app/src/click/__init__.py

#!/usr/bin/env sh
set -e

if [ "$#" -eq 0 ]; then
  set -- -h
fi

# Use exec so signals are passed directly to Python and preserve all args as-is.
exec python3 -m apifuzzer "$@"

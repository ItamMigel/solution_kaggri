#!/bin/bash
# usage: package_candidate.sh <src main.py> <candidate dir name>
set -euo pipefail
ROOT=/home/pavel-sardak/personal/kaggle/kaggriculture
SRC=$(readlink -f "$1"); DST=$ROOT/candidates/$2
mkdir -p "$DST"; cp "$SRC" "$DST/main.py"
cd "$DST"
"$ROOT/.venv/bin/python" -c "import ast; ast.parse(open('main.py').read())"
tar czf submission.tar.gz main.py
sha256sum main.py submission.tar.gz > sha256.txt
tar tzf submission.tar.gz
mkdir -p /place/vartmp/claude-743899/-home-pavel-sardak/546b4b50-77bf-42f9-9cef-3c46d4034eeb/scratchpad/pkgcheck_$$ && tar xzf submission.tar.gz -C /place/vartmp/claude-743899/-home-pavel-sardak/546b4b50-77bf-42f9-9cef-3c46d4034eeb/scratchpad/pkgcheck_$$ && cmp main.py /place/vartmp/claude-743899/-home-pavel-sardak/546b4b50-77bf-42f9-9cef-3c46d4034eeb/scratchpad/pkgcheck_$$/main.py && rm -rf /place/vartmp/claude-743899/-home-pavel-sardak/546b4b50-77bf-42f9-9cef-3c46d4034eeb/scratchpad/pkgcheck_$$ && echo "tar content verified"
sha256sum -c sha256.txt
ls -la "$DST"

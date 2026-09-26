#!/bin/bash
# Creates .venv and installs deps from your package index (artifactory). No internet needed if the index mirrors PyPI.
#   PIP_INDEX_URL=https://artifactory.company/api/pypi/pypi/simple  ./scripts/setup.sh
#   USE_SYSTEM_PYTHON=1 ./scripts/setup.sh    # skip venv, install into the current python (e.g. an existing torch env)
set -e; cd "$(dirname "$0")/.."
PYBIN=${PYBIN:-python3}
if [ "${USE_SYSTEM_PYTHON:-0}" = "1" ]; then PY=$PYBIN; else $PYBIN -m venv .venv; PY=.venv/bin/python; fi
$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt
$PY -m pip install --no-deps -r requirements-kaggle-env.txt
echo "$PY" > .python_path
$PY -c "import torch, numpy; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'gpus', torch.cuda.device_count(), 'numpy', numpy.__version__)"
$PY -c "import kaggle_environments, importlib.metadata as m; print('kaggle-environments', m.version('kaggle-environments'))" 2>&1 | grep -v pyspiel

#!/bin/bash
# Offline setup. Reuse the python of the BC/PPO package (it already has numpy + kaggle-environments 1.32.7):
#   PY=/opt/.../kaggri_bcppo_v3/.venv/bin/python ./scripts/setup.sh   (see kaggri_bcppo_v3/.python_path)
# pycma is pure python: the wheel is unpacked into ./pylib (no pip needed); scripts put it on PYTHONPATH.
set -e; cd "$(dirname "$0")/.."; PY=${PY:?set PY=/path/to/python with kaggle_environments}
rm -rf pylib; mkdir -p pylib; $PY -c "import zipfile,glob; zipfile.ZipFile(glob.glob('wheels/cma-*.whl')[0]).extractall('pylib')"
echo "$PY" > .python_path
PYTHONPATH=$PWD/pylib $PY -c "import cma, numpy, kaggle_environments; print('cma', cma.__version__, '| numpy', numpy.__version__, '| kaggle_environments', kaggle_environments.__version__)"
(cd harness && $PY compare.py --verify-only 2>&1 | tail -1)
echo SETUP_OK

# Offline H100/CPU-server packages (source of the zips in /workspace/shared/h100_pkg, which is git-ignored because of data/size)
- `bcppo_v3/` — scripts + README of kaggri_bcppo_v3 (BC→PPO on the exact GPU engine, PBT = evolution over PPO: scripts/pbt*.sh + lab/pbt/pbt_ctl.py).
  Code lives in lab/{gpuenv,bc,bcppo,pbt}; the zip adds data/bc_data and harness copies.
- `cma/` — CMA-ES over Horizon knobs on the server CPUs (scripts/run_cma.sh, gate.py = T025 fresh full-panel gate, gate_watch.sh);
  `tools_pkg/` = knob_es.py/knobs.py with package-relative paths (lab/tools versions keep the local absolute paths).
Build: zip is assembled from lab + harness files + data; see scripts in each README.

# T046 kit — fresh BC3 data build (Mac) + merge + fine-tune (4×H100)

## 1. Mac (M4): build 27.09 official episodes
```
cd t046_kit
python3.12 -m venv .venv && . .venv/bin/activate
pip install numpy jsonschema requests && pip install --no-deps kaggle-environments==1.32.7
pip install kaggle   # needs your Kaggle token (~/.kaggle/kaggle.json or KAGGLE_API_TOKEN)
kaggle datasets download kaggle/kaggriculture-episodes-2026-09-27 -p data      # 694 MB
cd lab/pavel/bc3
OMP_NUM_THREADS=1 python build_fresh.py --zips ../../../data/kaggriculture-episodes-2026-09-27.zip --out ../../../bc3_fresh_27 --workers 10
#   prints "N / 608" every 50 episodes, ends with BUILD_DONE; resumable (re-run skips episodes already in manifest.jsonl)
cd ../../.. && zip -r -0 bc3_fresh_27.zip bc3_fresh_27      # ~0.3-0.4 GB, NPZ are already compressed
```
Optional (if the Mac is fast): also 29.09 once it appears (~00:05 UTC 30.09): same with kaggriculture-episodes-2026-09-29.

## 2. GPU server: merge old (Pavel) + fresh zips into ONE dataset
Run from Pavel's lab/pavel/bc3 (or this kit's lab/pavel/bc3; feat3/feat must be importable):
```
python merge_datasets.py --src <pavel_old_bc3.zip or dir> --src bc3_fresh_28.zip --src bc3_fresh_27.zip \
       --out /data/bc3_merged --b1 --init <pavel>/bc3_runs/multi15_s0/best.pt
```
- OLD dataset FIRST (index 0); every later --src is FRESH -> its files get prefix f_ (used by --fresh-frac). Duplicates keep the first.
- Writes /data/bc3_merged (R0, original labels), /data/bc3_merged_b1 (R1, fixed day-boundary MOVE targets),
  /data/bc3_merged/val_ids.txt (fixed validation = 10% of fresh episodes, same for all runs) and prints the --data strings.
- NEW_* slots (DSM, Azat, ...) are merged but not used (no slot in m15 -> would change g_dim).

## 3. Fine-tune: 4 independent runs, one per GPU (Codex T046 recipe; 512 GB RAM is enough for 4 processes)
```
R=<pavel>/bc3_runs; V=/data/bc3_merged/val_ids.txt
DA=<--data string for bc3_merged>;  DB=<--data string for bc3_merged_b1>
C="--epochs 4 --bs 256 --lr 3e-5 --wd 1e-4 --pct-start 0.1 --fresh-frac 0.25 --val-ids $V --cpu-board"
CUDA_VISIBLE_DEVICES=0 nohup python train3_ft.py --data $DA --init $R/multi15_s0/best.pt --out runs/R0_s0 --seed 4600 $C > R0_s0.log 2>&1 &
CUDA_VISIBLE_DEVICES=1 nohup python train3_ft.py --data $DA --init $R/multi15_s1/best.pt --out runs/R0_s1 --seed 4601 $C > R0_s1.log 2>&1 &
CUDA_VISIBLE_DEVICES=2 nohup python train3_ft.py --data $DB --init $R/multi15_s0/best.pt --out runs/R1_s0 --seed 4600 $C > R1_s0.log 2>&1 &
CUDA_VISIBLE_DEVICES=3 nohup python train3_ft.py --data $DB --init $R/multi15_s1/best.pt --out runs/R1_s1 --seed 4601 $C > R1_s1.log 2>&1 &
```
- R0 = old 75% + fresh 25% of minibatch steps, original labels; R1 = same, B1-fixed targets. Architecture is taken from the init checkpoint.
- Log line `{"epoch": -1, ...}` = parent metrics on the new val split; `{"fresh_steps":..}` confirms the 25% mix.
- Each run saves e1..e4.pt, last.pt, best.pt. Bring back e2.pt, e4.pt (and best.pt) of all 4 runs (~50 MB each) — we export
  R0 = R0_s0+R0_s1 and R1 = R1_s0+R1_s1 as two separate agents (+HG d13, --fill --team mgoose_cn) and gate them here vs the parent.
- Do NOT average all 4 into one agent; do not mix R0/R1 members.

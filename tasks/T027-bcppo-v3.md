# T027 — BC→PPO v3: squeeze the training (claude + codex), 2026-09-25
Design: research/bcppo_v3_design.md; Codex audit: research/bcppo_v3_design_codex.md (pending).
H100 run 1 summary in tasks/T019-imitation.md. Human: GPUs only ~10 GB / 80 GB used.
## Log
- 16:20 Horizon-double data: lab/bc/gen_teacher.py (es3_g5 vs mirror/v5/es2c1/yhay0913/parthenos/metav4, seat alternates) → bc_data/es3, 3000 games running (runs/gen_es3.log).

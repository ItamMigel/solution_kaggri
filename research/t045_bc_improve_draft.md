# T045 — how to improve Pavel's BC+HG agent before the deadline (Claude draft for Codex critique), 2026-09-29 18:15Z
Deadline 2026-09-30 23:59 UTC (~29 h). Kaggle validation of a new upload reportedly can take up to 6 h → last useful upload ≈ 30.09 ~12:00-15:00Z.
After the deadline the 2 active subs keep playing ~2 weeks, then Bradley-Terry decides → true strength vs the field matters, not today's LB.

## Current state
- Active: bc_hg_mix4_d13 (56677106, LB 2392, 53-3 on ladder) + bc_hg_m15ens_d13 (56678587, climbing, ~1760 at 17:30Z).
- Pavel's code/notes (read-only checkout): /workspace/shared/pavel_lab/lab/pavel — README.md, notes/FINDINGS.md, notes/STATE.md,
  notes/HANDOFF_ADIL.md, bc3/ (feat3/build3/train3/export3/agent3), hg/hg_layer_v2.py, results/compare/*/README.md.
- Architecture: ResNet 8×128 on 10×10 board + global vector; per-unit heads (op, qty, target cell via attention); autoregressive GRU
  market decoder (≤10 ordered (op:item, qty) tokens); team one-hot (plays as Mother-Goose); 2-4 model ensemble (logit avg), numpy export (33 MB).
  Scripted "fill" when argmax is masked; herd guard (HG) days 0-13 (last-moment feeding + morning wheat reserve).
- Data: canonicalised (engine-replayed) market labels, 15 top teams, 1943 games (from 25.09 replays). Trained 16 epochs on Pavel's A100.
- Evidence: league 32 worlds × 2 vs 16-18 opponents: m15ens_d13 0.896, mix4_d13 0.83-0.87; h2h m15ens 59% vs mix4;
  Claude gate (12 worlds × 2): mix4_d13 vs g10c1 (best tetsu+market) 75% +6.6k, vs qA 88% +10.7k, vs tetsu 88% +8.7k, vs es7 92% +7.8k.
- Known weaknesses: V44 (Ozer) line 0.80-0.89; tetsu family 0.80 (mix4) / 0.95 (m15); stochastic (mirror ±13k).
- Negative results (Pavel): 3-4 model ensembles not better vs tetsu; WM wheat layer on BC hurts (0.54); M&M&P&Q/Boey team labels break policy.
- Our hardware: this box 48 CPU, no GPU worth using, 2.2 GB disk free. Human has 4×H100 (packages shipped as zip; human runs them).
  Pavel has A100 + all bc3 data/checkpoints. Engine ~1-2 min/game on CPU with BC (numpy ensemble is slow: first step 4-13 s, max step ~9-19 s under load; actTimeout 1 s + 60 s overage).

## Candidate directions (my ranking, please attack)
1. Fresh data: top-team replays from 27-29.09 (they updated agents) → re-canonicalise → fine-tune the same 2 models. 6-8 h. Gain unknown.
2. Advantage-/outcome-weighted BC on existing data (drop losses, weight by margin / opponent strength). One retrain. Small expected gain.
3. HG tuning vs V44 line (script only; CPU league here). Low risk, small gain.
4. DAgger-style: can't query experts; but can "self-correct" by relabelling states the BC visits with... nothing available. Skip?
5. RL fine-tune of BC on 4×H100: our gpuenv (lab/gpuenv, torch-batched engine, bit-exact vs old engine, needs re-difftest vs 1.32.7);
   KL-to-BC regularised PPO vs league. Previous BC→PPO (bcppo v3) never beat Horizon, but that BC was far weaker (old lossy codec).
   ~1 day of engineering + training → very risky for 29 h.
6. Test-time search: e.g. sample K market decodes / unit plans and pick by a value model or short rollout — too slow for 1 s/step budget?
7. Speed: faster numpy inference (fp16/int8, fewer blocks) to reduce timeout risk and allow bigger ensembles.
8. Mixed agent: BC for opening/mid-game + tetsu-style scripted endgame sales, or BC + our market layers only in days ≥20?

## Questions for Codex
Q1 Which of these (or others) has the best expected gain per hour given ~29 h and one human-operated 4×H100 box? Be quantitative where possible.
Q2 Read Pavel's code: any bugs / cheap wins (decoding: argmax vs sampling vs temperature; ensemble averaging in logit vs prob space; masking; fill rules; HG)?
Q3 Is RL (5) remotely feasible in time? What exactly would you run?
Q4 What would you *not* do (risk to the currently-silver active pair)?

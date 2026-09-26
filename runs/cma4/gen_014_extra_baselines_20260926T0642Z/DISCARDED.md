# Discarded CMA4 gen-14 evaluation

This evaluation completed its games but is not used in CMA state/history. The
rotating-panel launcher omitted the empty `--baselines`, so `compare.py` added
its three default baseline opponents. The intended six-opponent panel was
present, but the resulting 9-opponent output violated the exact-panel contract
and `_fitness_from_games` rejected it before `tell()`. The saved CMA pickle and
history remain at completed gen 13. A corrected re-run uses the same
predeclared deterministic gen-14 seeds and the explicit empty `--baselines`.
No Kaggle operation occurred.

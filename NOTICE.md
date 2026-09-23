# Attribution

This portable comparison kit includes the three frozen Horizon agent sources,
their archives, and local comparison tools. Research paths named below refer to
the original project; those downloads, datasets and research tools are not
redistributed in this kit. A completed audit report is in docs/stability_report.md.

The submission is an Apache-2.0 derivative of the public Kaggriculture policy
[The Soil Remembers Rain](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-the-soil-remembers-rain),
downloaded on 22 September 2026. The unchanged extracted source is
`vendor/soil_public.py`, SHA256
`bc80b476d9f3a714c8a357f57de8ca57012f6bd96cb2e204cab2a29a311b2323`.

The original source includes the Apache-2.0 license and inherited modification
and attribution notices. These remain in the standalone submission. Its lineage
credits Thomas Tschinkel, Yusuke Hayashi, destbreso, aurax7, Tetsutani, prvsiyan,
Dmitrii Gluzdov, Ahmed Berat Ozer and other authors identified in those notices.
This project does not claim their controllers, replay schedules, or embedded
forecast libraries as original work.

Local additions: final-day beam-search routing and labor selection,
finite-horizon livestock feeding decisions, reproducible packaging, evaluation
harness and parity checks, paired population search, recent public replay
processing, executed-sale learning, and held-out comparisons. See
`research/round2_notes.md`, `research/research_notes.md` and the per-game files
in `results/` for evidence. This does not claim the inherited production
schedules or forecast library as original work.

The game implementation is from
[Kaggle/kaggle-environments](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture).
Evaluation uses the installed official 1.32.7 interpreter. The C++ replay
screening implementation is Yusuke Hayashi's public
[kaggriculture-cpp-environment](https://www.kaggle.com/datasets/yhay81/kaggriculture-cpp-environment).
Its license and notice are retained with the local download. It is not part of
the submitted agent.

Recent replay data comes from Kaggle's public
[21 September episode dump](https://www.kaggle.com/datasets/kaggle/kaggriculture-episodes-2026-09-21).
The second research round also used publicly available episode JSON files from
Kaggle's episode service/CDN, following the access method documented in
[X-ray your agent](https://www.kaggle.com/code/destbreso/x-ray-your-agent) by
destbreso. The 58 recent training episode IDs, eight sale-library holdout IDs,
and the library hash are recorded in `submission_manifest.json`. The final
artifact embeds derived sale-pattern examples, not full replays. These recent
examples supplement the public parent's existing library.
The downloadable agent has no dependency on the Kaggle account, credentials,
local research files, external data directories, or network services.

The third research round adds multi-generation policy parameter search,
executed-action audits, neural imitation/forecasting experiments and stronger
validation. The release selects evolved sale timing; the experimental neural
models are not embedded in it. The prior public controller and local Horizon
v3 components retain their attribution above. See `research/round3_notes.md`.

Additional evaluation-only opponents were read from the Apache-2.0
[V43 sparse-shop notebook](https://www.kaggle.com/code/kaitofukami/103-128-fresh-public-v43-sparse-shop-hybrid)
and Jonathan Day's MIT-licensed
[lonespear/kaggriculture](https://github.com/lonespear/kaggriculture). Their
original notices and source provenance are retained locally. Their controllers
are not included in the submitted `main.py`.

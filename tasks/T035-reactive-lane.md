# T035 — clone-safe reactive lane

- Owner: codex. Deadline: 2026-09-28 18:00 UTC. Never submit.
- Base/control: `/workspace/shared/candidates/es7_wm/pkg/main.py`.
- Contract: default-off `reactive_lane`; decide only after at least six position checks in steps 216–222, and activate only if the rival matched none. A matching rival must receive byte-identical base actions.
- Proposed active lane: route-owned d9 third land, with owned access/placement/service; bounded d12–15 tomato+goose actions. Any failed precondition/mismatch aborts to base actions.
- Required checks: zero diffs vs base against mirror and three tape clones; activation against boatlee_v16/fukami_v48. CPU cap eight workers.

## Result

Implemented locally in `lab/hplus/reactive_lane.py`; it appends a self-contained layer to the exact es7_wm hash (`d1220b…`). The gene is default-off. Enabled mode records six calls from step 216, then only treats `matches == 0` as non-clone; any positional match remains base-only. The d9 order is delegated to `_hp_land`, which verifies a current-route future d11 `BUY_LAND`, confirms the observed land increase, and absorbs the original d11 debt. The d12 launch is limited to route hour 289, observed empty SW cells, two appended workers, one tomato seed and one goose; any precondition drift aborts later rewrites to base.

Official-engine audit (`runs/t035_reactive_lane/audit_required.json`, seed 135791): mirror and tape_unknown/tape_mmpq/tape_dsm have **0 action diffs**, all DONE; boatlee/fukami each have six checks, zero matches, `nonclone=1`, all DONE. Active-path probe seed 702 vs boatlee: `land_orders=land_confirmed=launches=tomato_plants=goose_places=1`, `aborts=errors=0`. Eight-worker bounded scan seeds 701–708 finds this full path only on 702; the other seven safely abstain because d9 cash is insufficient for the route-owned land. No score gate/candidate/submission action.

Next: extend daily hand ownership through d15 before any economic screen; current verified service is the d12 launch interval and returns to parent after the daily worker reset.

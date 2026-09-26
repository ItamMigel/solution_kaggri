"""top-RE plan layer: desired content per tile by day (DSM/MMPQ family, research/re_findings.md + re_production.md).
desired(obs, player) -> dict {(x, y): role}; role in CROPS ('WHEAT','MELON','STRAWBERRY','CARROT','TOMATO') or
'PASTURE:COW', 'PASTURE:SHEEP', 'COOP:GOOSE', or None (leave / harvest out). Coordinates are engine (x, y); tiles[y][x].
Also: targets(obs, player) -> macro targets for the market layer (hands, land timing, herd)."""
HALF = 5
def quad_tiles(q):
    xs = range(0, 5) if q[1] == "W" else range(5, 10); ys = range(0, 5) if q[0] == "N" else range(5, 10)
    return [(x, y) for y in ys for x in xs]
def _dist_shed(t):  # Manhattan distance to nearest shed-access tile
    return min(abs(t[0] - a) + abs(t[1] - b) for a, b in ((4, 4), (5, 4), (4, 5), (5, 5)))
def _by_shed(tiles): return sorted(tiles, key=lambda t: (_dist_shed(t), t[1], t[0]))

# ---- static layout (tiles closest to the shed host animals: daily FEED/CARE/HARVEST trips are shortest) ----
NW = _by_shed(quad_tiles("NW")); NE = _by_shed(quad_tiles("NE")); SW = _by_shed(quad_tiles("SW")); SE = _by_shed(quad_tiles("SE"))
LAYOUT = {
    # NW: 5 pastures (2 cows, 3 sheep) at d0; 8 melon (d0-2, exits d10-12 -> wheat); 12 wheat opening -> strawberry from d3
    "NW_PASTURE": NW[:5], "NW_MELON": NW[5:13], "NW_OPEN": NW[13:25],
    # NE (land #2 ~d6): 6 pastures (cows/sheep), 11 strawberry, 8 wheat
    "NE_PASTURE": NE[:6], "NE_STRAW": NE[6:17], "NE_WHEAT": NE[17:25],
    # SW (land #3 ~d8): 7 coops (geese) nearest the shed, 18 wheat (own feed + sales)
    "SW_COOP": SW[:7], "SW_WHEAT": SW[7:25],
}
NW_ANIMALS = ["PASTURE:COW", "PASTURE:COW", "PASTURE:SHEEP", "PASTURE:SHEEP", "PASTURE:SHEEP"]
NE_ANIMALS = ["PASTURE:COW", "PASTURE:COW", "PASTURE:COW", "PASTURE:COW", "PASTURE:SHEEP", "PASTURE:SHEEP"]

def desired(obs, player):
    day = int(obs["day"]); farm = obs["farms"][player]; quads = set(farm.get("unlocked_quadrants") or ["NW"]); want = {}
    for t, a in zip(LAYOUT["NW_PASTURE"], NW_ANIMALS): want[t] = a
    for t in LAYOUT["NW_MELON"]: want[t] = "MELON" if day <= 2 else ("WHEAT" if day <= 25 else "CARROT")
    for t in LAYOUT["NW_OPEN"]: want[t] = "WHEAT" if day <= 2 else ("STRAWBERRY" if day <= 22 else "CARROT")
    if "NE" in quads:
        for t, a in zip(LAYOUT["NE_PASTURE"], NE_ANIMALS): want[t] = a
        for t in LAYOUT["NE_STRAW"]: want[t] = "STRAWBERRY" if day <= 22 else "CARROT"
        for t in LAYOUT["NE_WHEAT"]: want[t] = "WHEAT" if day <= 26 else "CARROT"
    if "SW" in quads:
        for t in LAYOUT["SW_COOP"]: want[t] = "COOP:GOOSE"
        for t in LAYOUT["SW_WHEAT"]: want[t] = "WHEAT" if day <= 26 else "CARROT"
    if day >= 28:  # no new planting in the last 2 days: keep standing crops, plant nothing new
        want = {t: r for t, r in want.items() if ":" in r}
    return want

HANDS_BY_DAY = [5, 5, 5, 6, 6, 7, 9, 9, 10, 10, 11]  # day index -> hands target; 11 from d10 (DSM/MMPQ medians)
def targets(obs, player):
    day = int(obs["day"])
    return {"hands": HANDS_BY_DAY[min(day, len(HANDS_BY_DAY) - 1)] if day < 29 else 8,
            "land_step": {2: 147, 3: 196},  # quads after purchase -> earliest step (DSM/MMPQ median order steps)
            "wheat_reserve_per_animal": 2}

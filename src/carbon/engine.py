"""Independent Python implementation of the CarbonForm method (same rules as src/engine.js).

Written separately from the JavaScript so the test suite can compare the two line by line: if a formula is
changed in one place only, the parity test fails. Also used for the LCAbyg export and the report.
"""
from __future__ import annotations
import json, math
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PERIOD, START_YEAR = 50, 2026
LIMITS = dict(main=7.5, construction=1.5, main_2023=12.0, main_2027=6.4, main_2029=5.8)
EF_YEARS = [2025, 2030, 2035, 2040, 2045, 2050]
EF_EL = [0.0801, 0.0325, 0.0291, 0.0285, 0.0261, 0.0248]
EF_DH = [0.0418, 0.0181, 0.0140, 0.0134, 0.0132, 0.0132]
TRANSPORT_KM = dict(concrete_c30=30, concrete_c25=30, hollowcore=80, precast_wall20=80, precast_wall15=80, stair=80)
WASTE = dict(concrete_c30=0.02, concrete_c25=0.02, rebar=0.03, hollowcore=0.01, precast_wall20=0.01, precast_wall15=0.01,
             stair=0.0, door_steel=0.0)
DEFAULT_DESIGN = dict(mode="new", footprint="bar", length=48, depth=13, floors=5, storeyHeight=3.0, twist=0, setback=0,
                      structure="concrete", facade="brick", insulation="mineralwool", windows="woodalu", wwr=0.30,
                      roof="flat", pv=0.0, balconies=True, heating="district", topUpFloors=0)
R_OTHER = 0.4
U_NEW = dict(wall=0.15, roof=0.10, ground=0.10)
U_OLD = dict(wall=0.60, roof=0.40, ground=0.50, window=2.8)
INSUL = dict(mineralwool=("mw_facade", "mw_roof"), woodfibre=("wood_fibre", "wood_fibre"), eps=("eps", "eps"),
             cellulose=("cellulose", "cellulose"))
LAMBDA = dict(mineralwool=0.034, woodfibre=0.040, eps=0.031, cellulose=0.039)
STRUCT = {
    "concrete": dict(slab=dict(concrete_c30=0.22, rebar=19.8), intWall=dict(concrete_c30=0.18, rebar=10.8),
                     extBack=dict(concrete_c30=0.15, rebar=9.0), roofDeck=dict(concrete_c30=0.22, rebar=19.8), found=1.0),
    "precast": dict(slab=dict(hollowcore=1, concrete_c25=0.03), intWall=dict(precast_wall20=1), extBack=dict(precast_wall15=1),
                    roofDeck=dict(hollowcore=1, concrete_c25=0.03), found=0.95),
    "timber": dict(slab=dict(clt=0.16, concrete_c25=0.04, gypsum=2), intWall=dict(clt=0.10, gypsum=4),
                   extBack=dict(timber=0.025, gypsum=2), roofDeck=dict(clt=0.14), found=0.6),
    "steel": dict(slab=dict(hollowcore=1, steel_section=22, concrete_c25=0.03), intWall=dict(gypsum=4, steel_section=4),
                  extBack=dict(steel_section=8, gypsum=2), roofDeck=dict(hollowcore=1, steel_section=10), found=0.85),
}
CLADDING = dict(brick=(dict(brick=194.4, steel_section=2), 120), wood=(dict(larch=0.022, timber=0.006), 40),
                fibrecement=(dict(fibre_cement=1, steel_section=1.5), 50), render=(dict(etics_render=1), 40))
WINDOWS = dict(wood=("window_wood", 40, 0.80), woodalu=("window_woodalu", 40, 0.75), pvc=("window_pvc", 30, 0.85),
               curtain=("curtain_wall", 40, 0.90))
ROOF_FINISH = dict(flat=(dict(roofing_felt=1), 30), green=(dict(roofing_felt=1, green_roof=1), 40),
                   pitched=(dict(roof_tiles=52.5, timber=0.03), 60))
DEGREE_KH = 100


def load_db(path=None):
    return json.loads(Path(path or ROOT / "data/materials.json").read_text(encoding="utf-8"))


def ef(series, year):
    if year <= EF_YEARS[0]:
        return series[0]
    if year >= EF_YEARS[-1]:
        return series[-1]
    for i in range(len(EF_YEARS) - 1):
        if year <= EF_YEARS[i + 1]:
            t = (year - EF_YEARS[i]) / (EF_YEARS[i + 1] - EF_YEARS[i])
            return series[i] + t * (series[i + 1] - series[i])
    return series[-1]


def _area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def _perim(p):
    return sum(math.dist(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))


def footprint(d):
    L, D = d["length"], d["depth"]
    f = d["footprint"]
    if f == "L":
        W = max(D * 1.5, 0.6 * L); return [[0, 0], [L, 0], [L, D], [D, D], [D, W], [0, W]], []
    if f == "U":
        W = max(D * 1.8, 0.6 * L); return [[0, 0], [L, 0], [L, W], [L - D, W], [L - D, D], [D, D], [D, W], [0, W]], []
    if f == "courtyard":
        W = max(D * 2.6, 0.75 * L); return [[0, 0], [L, 0], [L, W], [0, W]], [[[D, D], [D, W - D], [L - D, W - D], [L - D, D]]]
    if f == "tower":
        s = max(D * 1.6, 16); return [[0, 0], [s, 0], [s, s], [0, s]], []
    return [[0, 0], [L, 0], [L, D], [0, D]], []


def geometry(d):
    outer, holes = footprint(d)
    area = _area(outer) - sum(_area(h) for h in holes)
    perim = _perim(outer) + sum(_perim(h) for h in holes)
    floors = d["floors"] + (d.get("topUpFloors", 0) if d["mode"] == "renovate" else 0)
    top_loss = min(area * 0.6, perim * d["setback"]) if d["setback"] > 0 and floors > 1 else 0
    gfa = area * floors - top_loss
    wall_gross = perim * d["storeyHeight"] * floors
    win = wall_gross * d["wwr"]
    roof = area / math.cos(math.radians(35)) if d["roof"] == "pitched" else area
    n_balc = floors * max(1, int(perim / 2 / 7)) if d["balconies"] else 0
    return dict(footprintArea=area, perimeter=perim, floors=floors, gfa=gfa, wallGross=wall_gross, windowArea=win,
                wallOpaque=wall_gross - win, roofArea=roof, nBalc=n_balc, cores=max(1, math.ceil(area / 450)))


def insulation_layer(kind, R, roof, db):
    mid = INSUL[kind][1 if roof else 0]
    m = db["materials"][mid]
    if m["unit"] == "m2R":
        return {mid: R}
    return {mid: R * LAMBDA[kind] * (m.get("density") or 43.75)}


def components(d, g, db):
    out = []
    reno = d["mode"] != "new"

    def add(key, group, qty, mats, life, existing=False):
        out.append(dict(key=key, group=group, qty=qty, mats=mats, life=life, existing=existing))

    S = STRUCT["concrete"] if reno else STRUCT[d["structure"]]
    bf = d["floors"]
    k = S["found"] * (bf / 5)
    add("foundation", "foundation", g["perimeter"], dict(concrete_c25=0.5 * k, rebar=20 * k), 120, reno)
    add("ground_slab", "foundation", g["footprintArea"], dict(concrete_c25=0.12, rebar=6), 120, reno)
    add("ground_insulation", "foundation", g["footprintArea"],
        insulation_layer("eps", 1.5 if reno else 1 / U_NEW["ground"] - R_OTHER, False, db), 120, reno)
    add("slabs", "structure", g["footprintArea"] * (bf - 1), S["slab"], 120, reno)
    add("int_walls", "structure", 0.30 * g["footprintArea"] * bf, S["intWall"], 120, reno)
    add("ext_backing", "structure", g["wallOpaque"] * (bf / g["floors"]), S["extBack"], 120, reno)
    add("roof_deck", "structure", g["footprintArea"], S["roofDeck"], 120, reno)
    add("stairs", "structure", g["cores"] * bf, dict(stair=1), 120, reno)
    tu = d.get("topUpFloors", 0)
    if d["mode"] == "renovate" and tu > 0:
        T = STRUCT["timber"]
        add("topup_slabs", "structure", g["footprintArea"] * tu, T["slab"], 120)
        add("topup_walls", "structure", 0.30 * g["footprintArea"] * tu, T["intWall"], 120)
        add("topup_ext", "structure", g["wallOpaque"] * tu / g["floors"], T["extBack"], 120)
        add("topup_stairs", "structure", g["cores"] * tu, dict(stair=1), 120)
    if d["mode"] == "keep":
        # ordinary maintenance of the unrenovated block: like-for-like windows and roofing on schedule
        add("maint_windows", "windows", g["windowArea"], dict(window_pvc=1), 30, "maintain")
        add("maint_roof", "roof", g["roofArea"], dict(roofing_felt=1), 30, "maintain")
        return out
    Rw = 1 / U_NEW["wall"] - 1 / U_OLD["wall"] if reno else 1 / U_NEW["wall"] - R_OTHER
    Rr = 1 / U_NEW["roof"] - 1 / U_OLD["roof"] if reno else 1 / U_NEW["roof"] - R_OTHER
    add("wall_insulation", "facade", g["wallOpaque"], insulation_layer(d["insulation"], Rw, False, db), 80)
    cm, cl = CLADDING[d["facade"]]
    add("cladding", "facade", g["wallOpaque"], cm, cl)
    wid, wl, _ = WINDOWS[d["windows"]]
    add("windows", "windows", g["windowArea"], {wid: 1}, wl)
    add("roof_insulation", "roof", g["footprintArea"], insulation_layer(d["insulation"], Rr, True, db), 80)
    rm, rl = ROOF_FINISH[d["roof"]]
    add("roof_finish", "roof", g["roofArea"], rm, rl)
    add("partitions", "interior", (0.3 if reno else 1) * g["gfa"], dict(gypsum=1.6, timber=0.002), 50)
    add("flooring", "interior", (0.5 if reno else 1) * g["gfa"] * 0.85, dict(parquet=1), 30)
    add("doors", "interior", math.ceil(g["gfa"] / 75), dict(door_steel=1), 40)
    if g["nBalc"] > 0:
        add("balconies", "balconies", g["nBalc"], dict(precast_wall20=5.25, steel_section=30), 80)
    if d["pv"] > 0 and d["roof"] != "green":
        add("pv", "energy", d["pv"] * g["footprintArea"] * 0.6, dict(pv=1), 30)
    return out


def energy(d, g):
    keep = d["mode"] == "keep"
    Uw = U_OLD["wall"] if keep else U_NEW["wall"]
    Ur = U_OLD["roof"] if keep else U_NEW["roof"]
    Ug = U_NEW["ground"] if d["mode"] == "new" else U_OLD["ground"]
    Uwin = U_OLD["window"] if keep else WINDOWS[d["windows"]][2]
    Htr = 1.10 * (Uw * g["wallOpaque"] + Ur * g["footprintArea"] + 0.5 * Ug * g["footprintArea"] + Uwin * g["windowArea"])
    mech, hr, infil = (0.0, 0.85, 0.50) if keep else (0.30, 0.85, 0.10)
    Hve = (mech * (1 - hr) + infil) * 1e-3 * g["gfa"] * 1200
    heat = max(0.0, (Htr + Hve) * DEGREE_KH - 0.8 * (20 * g["gfa"] + 61 * g["windowArea"]))
    dhw = 13 * g["gfa"]
    el_base = (3 if keep else 5) * g["gfa"]
    hp = d["heating"] == "heatpump" and not keep
    delivered = heat + dhw
    el_hp = delivered / 3.0 if hp else 0.0
    pv_area = d["pv"] * g["footprintArea"] * 0.6 if (d["pv"] > 0 and d["roof"] != "green" and not keep) else 0.0
    el_demand = el_base + el_hp
    pv_used = min(pv_area * 180, el_demand)
    return dict(heat=heat, dhw=dhw, elGrid=el_demand - pv_used, dhGrid=0.0 if hp else delivered, pvUsed=pv_used)


def _gwp(db, mid, mod):
    m = db["materials"][mid]
    v = m["gwp"].get(mod)
    return 0.0 if v is None else v / (m.get("per") or 1)


def _mass(db, mid, q):
    m = db["materials"][mid]
    u = m["unit"]
    if u == "kg":
        return q
    if u in ("m³", "m3"):
        return q * (m.get("density") or 0)
    if u == "m2R":
        return q * (m.get("lambda") or 0.035) * (m.get("density") or 30)
    if u in ("stk", "pcs"):
        return q * (m.get("mass_per_pcs") or 0)
    return q * (m.get("mass_per_m2") or 0)


def evaluate(design, db):
    d = {**DEFAULT_DESIGN, **(design or {})}
    g = geometry(d)
    truck = _gwp(db, "truck", "A4") / 1000
    mods = dict(A1A3=0.0, A4=0.0, A5=0.0, B4=0.0, B6=0.0, C3C4=0.0, D=0.0)
    events, groups = [], {}
    for c in components(d, g, db):
        n = max(0, math.ceil(PERIOD / c["life"]) - 1)
        r = dict(A1A3=0.0, A4=0.0, A5=0.0, B4=0.0, C3C4=0.0, D=0.0)
        for mid, per in c["mats"].items():
            q = per * c["qty"]
            a13 = q * _gwp(db, mid, "A1-A3")
            c34 = q * (_gwp(db, mid, "C3") + _gwp(db, mid, "C4"))
            if c["existing"] == "maintain":
                r["B4"] += n * (a13 + c34)
                continue
            if c["existing"]:
                r["C3C4"] += c34
                continue
            r["A1A3"] += a13; r["C3C4"] += c34; r["D"] += q * _gwp(db, mid, "D") * (1 + n)
            r["A4"] += _mass(db, mid, q) * TRANSPORT_KM.get(mid, 150) * truck
            r["A5"] += WASTE.get(mid, 0.05) * (a13 + c34)
            r["B4"] += n * (a13 + c34)
        events += [(i * c["life"], r["B4"] / n) for i in range(1, n + 1)]
        for k2 in mods:
            if k2 in r:
                mods[k2] += r[k2]
        groups[c["group"]] = groups.get(c["group"], 0) + r["A1A3"] + r["B4"] + r["C3C4"]
    inst_deferred = 0.0
    if True:  # installations in every scenario (an unrenovated block also renews HVAC/plumbing within 50 years)
        for mid in ("inst_drain", "inst_water", "inst_hvac"):
            a = g["gfa"] * PERIOD * _gwp(db, mid, "A1-A3")
            mods["A1A3"] += a
            if d["mode"] == "keep":
                inst_deferred += a          # renewed mid-life (year 25) in the timeline
            mods["C3C4"] += g["gfa"] * PERIOD * (_gwp(db, mid, "C3") + _gwp(db, mid, "C4"))
            mods["D"] += g["gfa"] * PERIOD * _gwp(db, mid, "D")
    site = g["gfa"] if d["mode"] == "new" else (0.35 * g["gfa"] if d["mode"] == "renovate" else 0)
    mods["A5"] += site * (15 * ef(EF_EL, START_YEAR) + 1.2 * 2.7)
    en = energy(d, g)
    b6 = [en["elGrid"] * ef(EF_EL, START_YEAR + i) + en["dhGrid"] * ef(EF_DH, START_YEAR + i) for i in range(PERIOD)]
    mods["B6"] = sum(b6)
    denom = g["gfa"] * PERIOD
    tl = [mods["A1A3"] + mods["A4"] + mods["A5"] - inst_deferred]
    for i in range(PERIOD):
        v = tl[i] + b6[i] + sum(kg for (yr, kg) in events if yr == i + 1) + (inst_deferred if i + 1 == 25 else 0)
        if i == PERIOD - 1:
            v += mods["C3C4"]
        tl.append(v)
    return dict(geometry=g, modules=mods, energy=en, groups=groups, timeline=tl,
                perM2Yr={k: v / denom for k, v in mods.items()},
                total=(mods["A1A3"] + mods["B4"] + mods["B6"] + mods["C3C4"]) / denom,
                construction=(mods["A4"] + mods["A5"]) / denom)

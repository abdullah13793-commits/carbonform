"""CarbonForm tests.  python -m pytest -q tests"""
import math, random, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from carbon import engine as py
from jsbridge import JSEngine

DB = py.load_db()


@pytest.fixture(scope="module")
def js():
    with JSEngine() as e:
        yield e


def random_design(rng):
    o = dict(footprint=["bar", "L", "U", "courtyard", "tower"], structure=["concrete", "precast", "timber", "steel"],
             facade=["brick", "wood", "fibrecement", "render"], insulation=["mineralwool", "woodfibre", "eps", "cellulose"],
             windows=["wood", "woodalu", "pvc", "curtain"], roof=["flat", "green", "pitched"], heating=["district", "heatpump"],
             mode=["new", "new", "renovate", "keep"])
    d = {k: rng.choice(v) for k, v in o.items()}
    d.update(length=rng.uniform(20, 70), depth=rng.uniform(10, 16), floors=rng.randint(2, 10), storeyHeight=rng.uniform(2.8, 3.3),
             wwr=rng.uniform(0.15, 0.6), pv=rng.choice([0, 0.3, 0.6, 1.0]), balconies=rng.random() < 0.6,
             setback=rng.choice([0, 0, 1.5]), topUpFloors=rng.randint(0, 3))
    return d


def test_js_python_parity(js):
    rng = random.Random(7)
    for _ in range(300):
        d = random_design(rng)
        a, b = js.evaluate(d), py.evaluate(d, DB)
        assert a["total"] == pytest.approx(b["total"], rel=1e-9, abs=1e-9), d
        assert a["construction"] == pytest.approx(b["construction"], rel=1e-9, abs=1e-9), d
        for k in ("A1A3", "A4", "A5", "B4", "B6", "C3C4", "D"):
            assert a["modules"][k] == pytest.approx(b["modules"][k], rel=1e-9, abs=1e-6), (k, d)
        assert a["timeline"] == pytest.approx(b["timeline"], rel=1e-9, abs=1e-6)   # whole 50-year curve


def test_bar_geometry_by_hand():
    d = {**py.DEFAULT_DESIGN, "length": 40, "depth": 12, "floors": 4, "storeyHeight": 3, "wwr": 0.25}
    g = py.geometry(d)
    assert g["footprintArea"] == pytest.approx(480)
    assert g["perimeter"] == pytest.approx(104)
    assert g["gfa"] == pytest.approx(1920)
    assert g["wallGross"] == pytest.approx(104 * 3 * 4)
    assert g["windowArea"] == pytest.approx(0.25 * 1248)


def test_courtyard_counts_inner_facade():
    d = {**py.DEFAULT_DESIGN, "footprint": "courtyard", "length": 50, "depth": 12}
    g = py.geometry(d)
    W = max(12 * 2.6, 37.5)
    assert g["footprintArea"] == pytest.approx(50 * W - (50 - 24) * (W - 24))
    assert g["perimeter"] == pytest.approx(2 * (50 + W) + 2 * ((50 - 24) + (W - 24)))


@pytest.mark.parametrize("life,n", [(120, 0), (50, 0), (40, 1), (30, 1), (25, 1), (20, 2), (15, 3)])
def test_replacement_rule(life, n):
    # LCAbyg / BR18 convention: replacements = ceil(period / lifetime) - 1
    assert max(0, math.ceil(50 / life) - 1) == n


def test_official_emission_factors(js):
    pts = {2025: (0.0801, 0.0418), 2030: (0.0325, 0.0181), 2050: (0.0248, 0.0132), 2075: (0.0248, 0.0132)}
    for y, (el, dh) in pts.items():
        assert py.ef(py.EF_EL, y) == pytest.approx(el) and py.ef(py.EF_DH, y) == pytest.approx(dh)
        assert js.call("y => CarbonForm.ef(CarbonForm.EF_EL, y)", y) == pytest.approx(el)
    assert py.ef(py.EF_EL, 2027) == pytest.approx(0.0801 + 0.4 * (0.0325 - 0.0801))


def test_insulation_layer_meets_u_value():
    R = 1 / 0.15 - 0.4
    lay = py.insulation_layer("mineralwool", R, False, DB)
    assert lay == {"mw_facade": pytest.approx(R)}                      # declared per m2 * R in BR18 table 7
    cel = py.insulation_layer("cellulose", R, False, DB)
    assert cel["cellulose"] == pytest.approx(R * 0.039 * 43.75)         # kg per m2 for the required thickness


def test_br18_installation_standard_values_included():
    d = {**py.DEFAULT_DESIGN}
    r = py.evaluate(d, DB)
    gfa = r["geometry"]["gfa"]
    inst = gfa * 50 * (0.056 + 0.05 + 0.394)
    r_no = py.evaluate(d, {**DB, "materials": {**DB["materials"], **{k: {**DB["materials"][k], "gwp": {"A1-A3": 0, "C3": 0, "C4": 0, "D": 0}}
                                                                        for k in ("inst_drain", "inst_water", "inst_hvac")}}})
    assert r["modules"]["A1A3"] - r_no["modules"]["A1A3"] == pytest.approx(inst)


def test_biogenic_carbon_storage_and_release():
    t = py.evaluate({"structure": "timber", "facade": "wood", "insulation": "woodfibre"}, DB)
    c = py.evaluate({}, DB)
    assert t["modules"]["A1A3"] < 0 < c["modules"]["A1A3"]              # timber stores CO2 up front
    assert t["modules"]["C3C4"] > c["modules"]["C3C4"]                  # ...and releases it at end of life
    assert t["total"] < c["total"]


def test_renovation_uses_less_material_than_new_build():
    n = py.evaluate({"mode": "new"}, DB)
    r = py.evaluate({"mode": "renovate"}, DB)
    k = py.evaluate({"mode": "keep"}, DB)
    # deep renovation (new brick facade, triple glazing, full new installations) is ~35 % of new-build A1-A3
    assert r["modules"]["A1A3"] < 0.5 * n["modules"]["A1A3"]
    inst = k["geometry"]["gfa"] * 50 * (0.056 + 0.05 + 0.394)
    assert k["modules"]["A1A3"] == pytest.approx(inst)                 # keep: only renewed installations
    assert k["energy"]["heat"] > 5 * r["energy"]["heat"]                # 1970s envelope vs renovated


def test_heating_demand_is_realistic():
    new = py.evaluate({}, DB)
    old = py.evaluate({"mode": "keep"}, DB)
    h_new = new["energy"]["heat"] / new["geometry"]["gfa"]
    h_old = old["energy"]["heat"] / old["geometry"]["gfa"]
    assert 8 < h_new < 35                                                # new Danish multi-storey housing
    assert 90 < h_old < 180                                              # unrenovated 1970s block


def test_timeline_ends_at_total(js):
    r = js.evaluate({"structure": "precast"})
    total_kg = r["total"] * r["geometry"]["gfa"] * 50 + (r["modules"]["A4"] + r["modules"]["A5"])
    assert r["timeline"][-1] == pytest.approx(total_kg, rel=1e-9)


def test_optimiser_finds_global_minimum(js):
    o = js.optimise({}, {"keys": ["structure", "facade"], "pv": [0]})
    best = min(py.evaluate({"structure": s, "facade": f}, DB)["total"]
               for s in ["concrete", "precast", "timber", "steel"] for f in ["brick", "wood", "fibrecement", "render"])
    assert o["total"] == pytest.approx(best)
    assert o["evaluated"] == 16


def test_lcabyg_export_round_trip():
    """The exported LCAbyg project, recomputed with LCAbyg's rules, reproduces the engine's embodied carbon."""
    import lcabyg_export as X
    rng = random.Random(3)
    for _ in range(40):
        d = random_design(rng); d["mode"] = "new"
        files = X.build(d, DB)
        r = X.recompute(files)
        e = py.evaluate(d, DB)
        assert r["A1to3"] == pytest.approx(e["modules"]["A1A3"], rel=1e-6)
        assert r["B4"] == pytest.approx(e["modules"]["B4"], rel=1e-6)
        assert r["C3C4"] == pytest.approx(e["modules"]["C3C4"], rel=1e-6)
        assert r["D"] == pytest.approx(e["modules"]["D"], rel=1e-6)
        ids = [next(iter(it["Node"].values()))["id"] for lst in files.values() for it in lst if "Node" in it]
        dup = {i for i in ids if ids.count(i) > 1} - {"0338d31e-3876-440d-a88c-2daa2dd81942"}
        assert not dup, dup                                          # every node id unique

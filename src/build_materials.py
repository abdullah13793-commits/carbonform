"""Build data/materials.json for CarbonForm.

Primary source: BR18 annex 2, table 7 (2025) "Generisk datagrundlag" - the generic dataset Danish building
regulations prescribe for LCA (bygningsreglementet.dk, tabel-7-2025.xlsx).
Supplementary (only where table 7 has no dataset): ÖKOBAUDAT 2024-II (green roof, truck transport).

python src/build_materials.py <tabel-7-2025.xlsx> <oekobaudat_2024II.csv>
"""
import csv, json, sys, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# CarbonForm id -> (BR18 table 7 sorting ID, English label, lambda W/mK for insulation per m2*R)
T7 = {
    "concrete_c30": ("#B1477", "Ready-mix concrete C30/37", None),
    "concrete_c25": ("#B1433", "Ready-mix concrete C25/30 (foundations, toppings)", None),
    "rebar": ("#D1590", "Reinforcing steel", None),
    "steel_section": ("#D1591", "Structural steel, rolled sections", None),
    "hollowcore": ("#B1346", "Hollow-core slab element, 22 cm", None),
    "precast_wall20": ("#B1389", "Precast concrete wall element, 20 cm", None),
    "precast_wall15": ("#B1385", "Precast concrete wall element, 15 cm", None),
    "clt": ("#B1318", "Cross-laminated timber (CLT)", None),
    "glulam": ("#B1339", "Glulam, spruce/pine", None),
    "timber": ("#B1489", "Structural timber, sawn and dried", None),
    "larch": ("#G0221", "Larch (cladding)", None),
    "brick": ("#D1508", "Facing brick (yellow/brown)", None),
    "fibre_cement": ("#D1514", "Fibre-cement board", None),
    "etics_render": ("#G1251", "ETICS adhesive + silicate render", None),
    "mw_facade": ("#D1536", "Mineral wool, hard, class 34", 0.034),
    "mw_roof": ("#D1537", "Mineral wool, hard, class 37", 0.037),
    "wood_fibre": ("#D1627", "Wood-fibre insulation board", 0.040),
    "eps": ("#D1560", "EPS insulation, grey, 60 kPa", 0.031),
    "cellulose": ("#D1623", "Cellulose (paper wool) insulation", 0.039),
    "window_wood": ("#D1635", "Timber window, triple glazed", None),
    "window_woodalu": ("#D1634", "Timber-aluminium window, triple glazed", None),
    "window_pvc": ("#D1632", "PVC window, triple glazed", None),
    "curtain_wall": ("#G0111", "Curtain wall, steel, triple glazed", None),
    "roofing_felt": ("#D1501", "Roofing felt, top + base layer", None),
    "roof_tiles": ("#D1497", "Clay roof tiles, red", None),
    "gypsum": ("#D1515", "Gypsum board, standard", None),
    "pv": ("#D1604", "PV panel, monocrystalline", None),
    "stair": ("#G0420", "Concrete stair, one storey", None),
    "door_steel": ("#G1222", "Steel door (apartment entrance)", None),
    "parquet": ("#G1166", "Multi-layer parquet", None),
    "inst_drain": ("#S0007", "Installations standard value: drainage (multi-storey housing)", None),
    "inst_water": ("#S0008", "Installations standard value: water (multi-storey housing)", None),
    "inst_hvac": ("#S0009", "Installations standard value: heating, ventilation, cooling (multi-storey housing)", None),
}
OEB = {
    "green_roof": ("7d3f45ad-d97f-467e-ae88-80e125400622", "Extensive green roof (ÖKOBAUDAT)"),
    "truck": ("bb74d2a2-249a-4245-a1bb-7bde61f2f613", "Truck transport (ÖKOBAUDAT, per 1000 kg·km)"),
}


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if f != f else f          # NaN (blank / '-' cells) -> 0


def main(t7_path, oeb_path):
    df = pd.read_excel(t7_path, header=0)
    df.columns = ["id", "type", "name_de", "name_dk", "A13", "C3", "C4", "D", "per", "unit", "mass", "mass_unit", "url", "comment"]
    df = df.set_index("id")
    out = {"_source": "BR18 bilag 2, tabel 7 (2025) generisk datagrundlag; supplementary ÖKOBAUDAT 2024-II where noted",
           "_extracted": datetime.date.today().isoformat(), "materials": {}}
    for mid, (tid, label, lam) in T7.items():
        r = df.loc[tid]
        unit = str(r.unit).strip()
        per = num(r.per) or 1.0
        g = {k: num(r[k]) for k in ("A13", "C3", "C4", "D")}
        mass, mu = num(r.mass), str(r.mass_unit)
        if unit == "ton":                        # normalise to per kg
            g = {k: v / 1000.0 for k, v in g.items()}; unit, per = "kg", 1.0
        if "with R=1" in unit:
            unit = "m2R"
        if tid.startswith("#S"):
            unit = "m2yr"                         # kg CO2e per m2 heated floor area per year
        rec = dict(label=label, name_dk=r.name_dk, source="BR18 tabel 7 (2025)", t7_id=tid, data_type=r.type,
                   unit=unit, per=per, gwp={"A1-A3": g["A13"], "C3": g["C3"], "C4": g["C4"], "D": g["D"]},
                   url=None if pd.isna(r.url) else r.url)
        if mu.startswith("kg/m³"): rec["density"] = mass
        elif mu.startswith("kg/m²"): rec["mass_per_m2"] = mass
        elif mu.startswith("kg/stk"): rec["mass_per_pcs"] = mass
        if lam: rec["lambda"] = lam
        out["materials"][mid] = rec
        print(f"{mid:16s} {tid:7s} {unit:5s} A1-A3 {g['A13']:10.4f} C3 {g['C3']:9.4f} C4 {g['C4']:8.4f} D {g['D']:9.4f}  {r.type}")
    rows = list(csv.DictReader(open(oeb_path, encoding="latin-1"), delimiter=";"))
    for mid, (uuid, label) in OEB.items():
        rs = [r for r in rows if r["UUID"] == uuid]
        latest = max(r["Version"] for r in rs)
        gw = {}
        for r in rs:
            if r["Version"] == latest:
                v = r.get("GWPtotal (A2)") or r.get("GWP")
                if v: gw[r["Modul"]] = float(v)
        u = rs[0]["Bezugseinheit"]
        rec = dict(label=label, source="ÖKOBAUDAT 2024-II", uuid=uuid, unit={"qm": "m2"}.get(u, u),
                   per=float(rs[0]["Bezugsgroesse"] or 1), gwp=gw, url=rs[0]["URL"])
        if mid == "green_roof": rec["mass_per_m2"] = 100.0
        out["materials"][mid] = rec
        print(f"{mid:16s} OEB     {rec['unit']:5s} {gw}")
    (ROOT / "data").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "data/materials.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("->", ROOT / "data/materials.json", len(out["materials"]), "materials")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

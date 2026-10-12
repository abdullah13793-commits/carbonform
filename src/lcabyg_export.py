"""Export a CarbonForm design as an LCAbyg 5 (LCAbyg 2023) JSON import project.

Follows the node/edge structure of the official LCAbyg JSON guide (import_example): Project -> Building ->
EmbodiedRoot -> ElementModel -> element categories (built-in gen_dk IDs) -> Element -> Construction -> Product -> Stage.
Products and stages carry the same BR18 table 7 data the CarbonForm engine uses, so LCAbyg calculates the
embodied impact with identical inputs; operational energy goes into the Operation node (kWh/m2/yr).

python src/lcabyg_export.py [design.json] [out_dir]      -> out_dir/*.json + out_dir.zip
"""
from __future__ import annotations
import json, math, sys, uuid, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from carbon import engine as E

ROOT = Path(__file__).resolve().parents[1]
NS = uuid.UUID("6f1c9a52-6c0b-4f1e-9c3e-2a7c0f6b9d11")

# fixed IDs from the official import example (project skeleton) and gen_dk (built-in library)
EX = dict(project="e9e6e798-390e-4419-a1fa-3b46a8ba5b8d", root="216cf5d6-3e9d-43ec-b0d8-5aee02240c28",
          model="aeefab8a-e825-4d14-b0c3-e87b7759e5b2", process="349738da-9747-4d5c-b508-2a810317166f",
          op_main="0338d31e-3876-440d-a88c-2daa2dd81942", op_install="c33cf608-9ceb-47f3-9ccf-c3ecb58ddb96",
          el_source="e967c8e7-e73d-47f3-8cba-19569ad76b4d", dh_source="d92c95dc-cd10-4eb1-821d-5c724d9cafb8",
          el_source2="84ddd0e5-85a1-48cb-ab90-aa19b3359458", stage_cat="4cf6cca4-0814-42d3-b26d-c0dd3792bccd")
SUPER_CATS = ["0ae65810-51bc-4130-89a0-9c107f1aca3f", "20c75334-735c-442f-a541-985ac5a130c8", "9e7adf74-5281-4aa4-9cff-d903a4266aae",
              "bae7f4b9-967c-4542-bc99-f744aa261424", "ca17092d-2a42-4941-b478-669b12001556", "487184b7-5568-497b-b7e2-e8d2269e51ef",
              "a1746ce9-3d06-424c-a701-34a090f08433", "571650a7-4259-4cc1-9d56-a12e516fd495", "e5937376-1d7f-4edf-9710-cafd7fe91606",
              "6808ac7b-2a79-45a6-8013-5f89ad13c337", "f7737ac7-ea51-488e-81de-9c1bab1c08bf", "3cb417d3-d615-402e-81dc-d7d587e83ac1",
              "ac7112e7-ccea-4e1b-a6a2-9c9c3b9a7177", "1e853d01-fce5-4947-850d-e0b43e51b1fc", "d50ad0a5-636a-4169-b4d7-21e9b64d94a8",
              "dad100a3-f570-4c96-bec0-9028bc5f6835", "de3a2393-388c-4079-9e7d-6529c14f8a69"]
CATEGORY = {  # CarbonForm component key -> gen_dk element category (name, id)
    "foundation": ("Randfundamenter", "1a966c7c-fd7c-4abc-9d4b-307fdcd0cc88"),
    "ground_slab": ("Terrændæk", "2ffe16fd-f0c9-4d31-a31a-f96d58d3df95"),
    "ground_insulation": ("Terrændæk", "2ffe16fd-f0c9-4d31-a31a-f96d58d3df95"),
    "slabs": ("Etagedæk", "f4c234ec-77f1-4ee0-92d0-f1819e0307d4"),
    "topup_slabs": ("Etagedæk", "f4c234ec-77f1-4ee0-92d0-f1819e0307d4"),
    "int_walls": ("Bærende indervægge", "59ab59a5-2482-45ae-85f1-d0e39e640712"),
    "topup_walls": ("Bærende indervægge", "59ab59a5-2482-45ae-85f1-d0e39e640712"),
    "ext_backing": ("Ydervægge", "10a52123-48d7-466a-9622-d463511a6df0"),
    "topup_ext": ("Ydervægge", "10a52123-48d7-466a-9622-d463511a6df0"),
    "wall_insulation": ("Ydervægge", "10a52123-48d7-466a-9622-d463511a6df0"),
    "cladding": ("Ydervægge", "10a52123-48d7-466a-9622-d463511a6df0"),
    "roof_deck": ("Tage", "d734712a-d27d-42c5-936f-98fe4c4df90b"),
    "roof_insulation": ("Tage", "d734712a-d27d-42c5-936f-98fe4c4df90b"),
    "roof_finish": ("Tage", "d734712a-d27d-42c5-936f-98fe4c4df90b"),
    "stairs": ("Trapper og ramper", "1caeddce-29e9-4067-b85b-36e8d103a4a0"),
    "topup_stairs": ("Trapper og ramper", "1caeddce-29e9-4067-b85b-36e8d103a4a0"),
    "windows": ("Vinduer", "dcbf55db-3189-4d22-9b2b-2e27c057b363"),
    "partitions": ("Ikke-bærende indervægge", "a9ab6709-61e1-46c1-a2e8-df00bdd0bb91"),
    "flooring": ("Belægninger", "14bdd9bc-fc11-4846-b89d-5434dd04b773"),
    "doors": ("Døre", "9bd14e05-5fba-4ecb-ab41-7940a8a0dbdc"),
    "balconies": ("Altanbund", "a48092d1-8b5c-4fa9-9ada-69cec3fd1dca"),
    "pv": ("Energiproduktion", "dc4a81ce-2d10-4fba-b282-a3cce4e9a187"),
    "installations": ("Ventilationsanlæg", "cf702d99-5d5a-4973-ba9c-c4dbfae656a9"),
}
UNIT = {"m³": "M3", "m3": "M3", "m²": "M2", "m2": "M2", "kg": "KG", "stk": "PCS", "pcs": "PCS", "m": "M"}
STAGE_KEYS = [("A1-A3", "A1to3"), ("C3", "C3"), ("C4", "C4"), ("D", "D")]
INDICATORS0 = dict(GWP=0, ODP=0, POCP=0, AP=0, EP=0, ADPE=0, ADPF=0, PENR=0, PER=0, SENR=0.0, SER=0.0)


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


def node(kind, **f):
    return {"Node": {kind: f}}


def edge(kind, payload, a, b):
    return {"Edge": [{kind: payload}, a, b]}


def product_spec(mid, db):
    """LCAbyg unit, mass factor and per-unit GWP by stage for one material (insulation per m2*R -> per kg)."""
    m = db["materials"][mid]
    g = {k: (m["gwp"].get(k) or 0.0) / (m.get("per") or 1) for k, _ in STAGE_KEYS}
    if m["unit"] == "m2R":                       # per m2 at R=1  ->  per kg
        kg_per_m2R = m["lambda"] * m["density"]
        return "KG", 1.0, {k: v / kg_per_m2R for k, v in g.items()}, kg_per_m2R
    u = UNIT.get(m["unit"], "M2")
    mass = m.get("density") if u == "M3" else m.get("mass_per_m2") if u == "M2" else m.get("mass_per_pcs") if u == "PCS" else 1.0
    return u, float(mass or 1.0), g, 1.0


def build(design: dict, db: dict):
    d = {**E.DEFAULT_DESIGN, **(design or {})}
    g = E.geometry(d)
    comps = [c for c in E.components(d, g, db) if not c["existing"]]
    en = E.energy(d, g)
    files: dict[str, list] = {k: [] for k in ("project", "building", "embodied_root", "element_model", "elements",
                                                  "element_category_edges", "constructions", "constructions_extra",
                                                  "products", "stages", "operation", "construction_process")}
    bid = uid("building", json.dumps(d, sort_keys=True))
    files["project"].append(node("Project", id=EX["project"]))
    files["building"] += [
        node("Building", id=bid, name={"Danish": f"CarbonForm {d['structure']}/{d['facade']} {g['floors']} etager",
                                       "English": "CarbonForm export", "German": ""},
             address="CarbonForm", owner="CarbonForm", description="Exported from CarbonForm (BR18 tabel 7 data)",
             building_type="Other", heated_floor_area=round(g["gfa"], 2), gross_area=round(g["gfa"], 2),
             gross_area_above_ground=round(g["gfa"], 2), storeys_above_ground=g["floors"], storeys_below_ground=0,
             storey_height=d["storeyHeight"], initial_year=E.START_YEAR, calculation_timespan=E.PERIOD, calculation_mode="SC",
             lca_advisor="CarbonForm", building_regulation_version="BR2018", plot_area=round(g["footprintArea"] * 3, 1),
             outside_area=0, energy_class="LowEnergy"),
        edge("MainBuilding", uid("mb", bid), EX["project"], bid),
        edge("BuildingToRoot", uid("btr", bid), bid, EX["root"]),
        edge("BuildingToOperation", uid("bto", bid), bid, EX["op_main"]),
    ]
    files["embodied_root"] += [node("EmbodiedRoot", id=EX["root"]),
                               edge("RootToModel", uid("rtm", bid), EX["root"], EX["model"]),
                               edge("RootToConstructionProcess", uid("rtcp", bid), EX["root"], EX["process"])]
    files["element_model"].append(node("ElementModel", id=EX["model"]))
    files["element_model"] += [edge("ParentTo", uid("pt", s), EX["model"], s) for s in SUPER_CATS]
    files["construction_process"] += [node("ConstructionProcess", id=EX["process"])]
    files["operation"] += [
        node("Operation", id=EX["op_main"], electricity_usage=round(en["elGrid"] / g["gfa"], 3),
             heat_usage=round(en["dhGrid"] / g["gfa"], 3), electricity_production=0),
        edge("ElectricitySource", uid("es", bid), EX["op_main"], EX["el_source"]),
        edge("HeatingSource", uid("hs", bid), EX["op_main"], EX["dh_source"]),
        node("Operation", id=EX["op_install"], electricity_usage=0, heat_usage=0, electricity_production=0.0),
        edge("ElectricitySource", uid("es2", bid), EX["op_install"], EX["el_source"]),
        edge("HeatingSource", uid("hs2", bid), EX["op_install"], EX["el_source2"]),
    ]
    made_products = {}

    def product(mid):
        if mid in made_products:
            return made_products[mid]
        m = db["materials"][mid]
        unit, mass, gw, conv = product_spec(mid, db)
        pid = uid("product", mid)
        files["products"].append(node("Product", id=pid, name={"Danish": f"CF {m.get('name_dk', m['label'])}"[:120],
                                                                   "English": f"CF {m['label']}", "German": ""},
                                      source="User", comment=f"{m.get('source')} {m.get('t7_id', m.get('uuid', ''))}", locked=True))
        for k, stage in STAGE_KEYS:
            if abs(gw[k]) < 1e-12 and stage != "A1to3":
                continue
            sid = uid("stage", mid, stage)
            ind = dict(INDICATORS0, GWP=gw[k])
            files["stages"].append(node("Stage", id=sid, name={"Danish": f"CF {m['label']} ({k})", "English": f"CF {m['label']} ({k})", "German": ""},
                                        comment="", source="User", locked=True, valid_to="2030-12-31", stage=stage,
                                        stage_unit=unit, indicator_unit=unit, stage_factor=1.0, mass_factor=mass, indicator_factor=1.0,
                                        external_source=m.get("source", ""), external_id=m.get("t7_id", m.get("uuid", "")),
                                        external_version="2025", external_url=m.get("url") or "", indicators=ind))
            files["stages"].append(edge("ProductToStage", {"id": uid("pts", mid, stage), "enabled": True}, pid, sid))
            files["stages"].append(edge("Generic", uid("sc", mid, stage), EX["stage_cat"], sid))
        made_products[mid] = (pid, unit, conv)
        return made_products[mid]

    def construction(key, unit, mats, life, qty):
        eid, cid = uid("element", key, bid), uid("construction", key, bid)
        cat_name, cat = CATEGORY[key]
        files["elements"] += [
            node("Element", id=eid, name={"Danish": f"CF {key}", "English": f"CF {key}", "German": ""}, source="User",
                 comment="", enabled=True, active=True),
            edge("ElementToConstruction", {"id": uid("etc", key, bid), "amount": round(qty, 4), "enabled": True}, eid, cid)]
        files["element_category_edges"].append(edge("CategoryToElement", {"id": uid("cte", key, bid), "enabled": True}, cat, eid))
        files["constructions"].append(node("Construction", id=cid, name={"Danish": f"CF {key}"}, unit=unit, source="User",
                                           comment=cat_name, layer=1, locked=True))
        files["constructions_extra"].append(edge("CategoryToConstruction", {"id": uid("ctc", key, bid), "layers": [1]}, cat, cid))
        for mid, per in mats.items():
            pid, punit, conv = product(mid)
            files["constructions"].append(edge("ConstructionToProduct",
                                               {"id": uid("ctp", key, mid, bid), "amount": round(per * conv, 6), "unit": punit,
                                                "lifespan": life, "demolition": False, "enabled": True, "delayed_start": 0},
                                               cid, pid))

    unit_of = {"m2": "M2", "m": "M", "pcs": "PCS"}
    for c in comps:
        construction(c["key"], unit_of.get(_unit(c), "M2"), c["mats"], c["life"], c["qty"])
    if d["mode"] != "keep":
        # BR18 standard values for installations (kg CO2e/m2/yr) -> one product per m2 for the whole period
        mats = {}
        for mid in ("inst_drain", "inst_water", "inst_hvac"):
            mats[mid] = 1.0
        construction("installations", "M2", {}, 100, g["gfa"])
        for mid in mats:
            m = db["materials"][mid]
            pid = uid("product", mid)
            files["products"].append(node("Product", id=pid, name={"Danish": f"CF {m['name_dk']}", "English": f"CF {m['label']}", "German": ""},
                                          source="User", comment=f"BR18 standardværdi {m['t7_id']} x {E.PERIOD} år", locked=True))
            for k, stage in STAGE_KEYS:
                v = (m["gwp"].get(k) or 0.0) * E.PERIOD
                if abs(v) < 1e-12 and stage != "A1to3":
                    continue
                sid = uid("stage", mid, stage)
                files["stages"].append(node("Stage", id=sid, name={"Danish": f"CF {m['label']} ({k})", "English": "", "German": ""},
                                            comment="", source="User", locked=True, valid_to="2030-12-31", stage=stage,
                                            stage_unit="M2", indicator_unit="M2", stage_factor=1.0, mass_factor=1.0,
                                            indicator_factor=1.0, external_source="BR18 tabel 7 (2025)", external_id=m["t7_id"],
                                            external_version="2025", external_url="", indicators=dict(INDICATORS0, GWP=v)))
                files["stages"].append(edge("ProductToStage", {"id": uid("pts", mid, stage), "enabled": True}, pid, sid))
                files["stages"].append(edge("Generic", uid("sc", mid, stage), EX["stage_cat"], sid))
            files["constructions"].append(edge("ConstructionToProduct",
                                               {"id": uid("ctp", "installations", mid, bid), "amount": 1.0, "unit": "M2",
                                                "lifespan": 100, "demolition": False, "enabled": True, "delayed_start": 0},
                                               uid("construction", "installations", bid), pid))
    return files


def _unit(c):
    return {"foundation": "m", "stairs": "pcs", "topup_stairs": "pcs", "doors": "pcs", "balconies": "pcs"}.get(c["key"], "m2")


def recompute(files) -> dict:
    """Re-read an export with LCAbyg's rules (amount x stage factor, replacements from lifespan, 50 years)."""
    stages, prod_stages, cons_prod, elem_cons = {}, {}, {}, {}
    for lst in files.values():
        for it in lst:
            if "Node" in it and "Stage" in it["Node"]:
                s = it["Node"]["Stage"]; stages[s["id"]] = (s["stage"], s["indicators"]["GWP"])
            if "Edge" in it:
                (kind, pay), a, b = next(iter(it["Edge"][0].items())), it["Edge"][1], it["Edge"][2]
                if kind == "ProductToStage": prod_stages.setdefault(a, []).append(b)
                if kind == "ConstructionToProduct": cons_prod.setdefault(a, []).append((b, pay["amount"], pay["lifespan"]))
                if kind == "ElementToConstruction": elem_cons[b] = pay["amount"]
    out = dict(A1to3=0.0, B4=0.0, C3C4=0.0, D=0.0)
    for cid, qty in elem_cons.items():
        for pid, amount, life in cons_prod.get(cid, []):
            n = max(0, math.ceil(E.PERIOD / life) - 1)
            vals = {st: v for st, v in (stages[s] for s in prod_stages.get(pid, []))}
            a13 = qty * amount * vals.get("A1to3", 0); c34 = qty * amount * (vals.get("C3", 0) + vals.get("C4", 0))
            out["A1to3"] += a13; out["C3C4"] += c34; out["B4"] += n * (a13 + c34); out["D"] += qty * amount * vals.get("D", 0) * (1 + n)
    return out


def write(files, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, items in files.items():
        (out_dir / f"{name}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    z = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out_dir.glob("*.json")):
            zf.write(p, f"{out_dir.name}/{p.name}")
    return z


if __name__ == "__main__":
    design = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else {}
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "exports/lcabyg_carbonform"
    db = E.load_db()
    files = build(design, db)
    z = write(files, out)
    r = recompute(files); e = E.evaluate(design, db)
    print("export ->", z)
    print("recomputed A1-A3 %.0f kg vs engine %.0f kg" % (r["A1to3"], e["modules"]["A1A3"]))

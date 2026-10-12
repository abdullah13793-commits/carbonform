/* Browser port of src/lcabyg_export.py: CarbonForm design -> LCAbyg 5 (LCAbyg 2023) JSON import files.
 * Same node/edge structure as the Python exporter; the test suite checks both recompute to the engine totals. */
(function (root) {
  "use strict";
  const CF = root.CarbonForm;
  const EX = { project: "e9e6e798-390e-4419-a1fa-3b46a8ba5b8d", root: "216cf5d6-3e9d-43ec-b0d8-5aee02240c28",
    model: "aeefab8a-e825-4d14-b0c3-e87b7759e5b2", process: "349738da-9747-4d5c-b508-2a810317166f",
    op_main: "0338d31e-3876-440d-a88c-2daa2dd81942", op_install: "c33cf608-9ceb-47f3-9ccf-c3ecb58ddb96",
    el_source: "e967c8e7-e73d-47f3-8cba-19569ad76b4d", dh_source: "d92c95dc-cd10-4eb1-821d-5c724d9cafb8",
    el_source2: "84ddd0e5-85a1-48cb-ab90-aa19b3359458", stage_cat: "4cf6cca4-0814-42d3-b26d-c0dd3792bccd" };
  const SUPER = ["0ae65810-51bc-4130-89a0-9c107f1aca3f", "20c75334-735c-442f-a541-985ac5a130c8", "9e7adf74-5281-4aa4-9cff-d903a4266aae",
    "bae7f4b9-967c-4542-bc99-f744aa261424", "ca17092d-2a42-4941-b478-669b12001556", "487184b7-5568-497b-b7e2-e8d2269e51ef",
    "a1746ce9-3d06-424c-a701-34a090f08433", "571650a7-4259-4cc1-9d56-a12e516fd495", "e5937376-1d7f-4edf-9710-cafd7fe91606",
    "6808ac7b-2a79-45a6-8013-5f89ad13c337", "f7737ac7-ea51-488e-81de-9c1bab1c08bf", "3cb417d3-d615-402e-81dc-d7d587e83ac1",
    "ac7112e7-ccea-4e1b-a6a2-9c9c3b9a7177", "1e853d01-fce5-4947-850d-e0b43e51b1fc", "d50ad0a5-636a-4169-b4d7-21e9b64d94a8",
    "dad100a3-f570-4c96-bec0-9028bc5f6835", "de3a2393-388c-4079-9e7d-6529c14f8a69"];
  const CAT = { foundation: "1a966c7c-fd7c-4abc-9d4b-307fdcd0cc88", ground_slab: "2ffe16fd-f0c9-4d31-a31a-f96d58d3df95",
    ground_insulation: "2ffe16fd-f0c9-4d31-a31a-f96d58d3df95", slabs: "f4c234ec-77f1-4ee0-92d0-f1819e0307d4",
    topup_slabs: "f4c234ec-77f1-4ee0-92d0-f1819e0307d4", int_walls: "59ab59a5-2482-45ae-85f1-d0e39e640712",
    topup_walls: "59ab59a5-2482-45ae-85f1-d0e39e640712", ext_backing: "10a52123-48d7-466a-9622-d463511a6df0",
    topup_ext: "10a52123-48d7-466a-9622-d463511a6df0", wall_insulation: "10a52123-48d7-466a-9622-d463511a6df0",
    cladding: "10a52123-48d7-466a-9622-d463511a6df0", roof_deck: "d734712a-d27d-42c5-936f-98fe4c4df90b",
    roof_insulation: "d734712a-d27d-42c5-936f-98fe4c4df90b", roof_finish: "d734712a-d27d-42c5-936f-98fe4c4df90b",
    stairs: "1caeddce-29e9-4067-b85b-36e8d103a4a0", topup_stairs: "1caeddce-29e9-4067-b85b-36e8d103a4a0",
    windows: "dcbf55db-3189-4d22-9b2b-2e27c057b363", partitions: "a9ab6709-61e1-46c1-a2e8-df00bdd0bb91",
    flooring: "14bdd9bc-fc11-4846-b89d-5434dd04b773", doors: "9bd14e05-5fba-4ecb-ab41-7940a8a0dbdc",
    balconies: "a48092d1-8b5c-4fa9-9ada-69cec3fd1dca", pv: "dc4a81ce-2d10-4fba-b282-a3cce4e9a187",
    installations: "cf702d99-5d5a-4973-ba9c-c4dbfae656a9" };
  const UNIT = { "m³": "M3", m3: "M3", "m²": "M2", m2: "M2", kg: "KG", stk: "PCS", pcs: "PCS", m: "M" };
  const STAGES = [["A1-A3", "A1to3"], ["C3", "C3"], ["C4", "C4"], ["D", "D"]];
  const IND0 = { GWP: 0, ODP: 0, POCP: 0, AP: 0, EP: 0, ADPE: 0, ADPF: 0, PENR: 0, PER: 0, SENR: 0.0, SER: 0.0 };

  // deterministic RFC-4122-shaped id from a string (FNV-1a based; uniqueness is what LCAbyg needs)
  function uid() {
    const s = Array.from(arguments).join("/");
    const h = [0x811c9dc5, 0x01000193, 0x9e3779b9, 0x85ebca6b].map(seed => {
      let x = seed >>> 0;
      for (let i = 0; i < s.length; i++) { x ^= s.charCodeAt(i); x = Math.imul(x, 16777619) >>> 0; x ^= seed; }
      return ("00000000" + (x >>> 0).toString(16)).slice(-8);
    }).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-5${h.slice(13, 16)}-a${h.slice(17, 20)}-${h.slice(20, 32)}`;
  }
  const node = (k, f) => ({ Node: { [k]: f } });
  const edge = (k, p, a, b) => ({ Edge: [{ [k]: p }, a, b] });
  const unitOf = key => ({ foundation: "M", stairs: "PCS", topup_stairs: "PCS", doors: "PCS", balconies: "PCS" }[key] || "M2");

  function productSpec(id, DB) {
    const m = DB.materials[id];
    const g = {}; for (const [k] of STAGES) g[k] = (m.gwp[k] || 0) / (m.per || 1);
    if (m.unit === "m2R") { const kg = m.lambda * m.density; const o = {}; for (const k in g) o[k] = g[k] / kg; return ["KG", 1, o, kg]; }
    const u = UNIT[m.unit] || "M2";
    const mass = u === "M3" ? m.density : u === "M2" ? m.mass_per_m2 : u === "PCS" ? m.mass_per_pcs : 1;
    return [u, mass || 1, g, 1];
  }

  function build(design, DB) {
    const d = Object.assign({}, CF.DEFAULT_DESIGN, design || {});
    const g = CF.geometry(d);
    const comps = CF.components(d, g, DB).filter(c => !c.existing);
    const en = CF.energy(d, g);
    const F = { project: [], building: [], embodied_root: [], element_model: [], elements: [], element_category_edges: [],
                constructions: [], constructions_extra: [], products: [], stages: [], operation: [], construction_process: [] };
    const bid = uid("building", JSON.stringify(d));
    F.project.push(node("Project", { id: EX.project }));
    F.building.push(node("Building", { id: bid, name: { Danish: `CarbonForm ${d.structure}/${d.facade} ${g.floors} etager`, English: "CarbonForm export", German: "" },
      address: "CarbonForm", owner: "CarbonForm", description: "Exported from CarbonForm (BR18 tabel 7 data)", building_type: "Other",
      heated_floor_area: +g.gfa.toFixed(2), gross_area: +g.gfa.toFixed(2), gross_area_above_ground: +g.gfa.toFixed(2),
      storeys_above_ground: g.floors, storeys_below_ground: 0, storey_height: d.storeyHeight, initial_year: CF.START_YEAR,
      calculation_timespan: CF.PERIOD, calculation_mode: "SC", lca_advisor: "CarbonForm", building_regulation_version: "BR2018",
      plot_area: +(g.footprintArea * 3).toFixed(1), outside_area: 0, energy_class: "LowEnergy" }),
      edge("MainBuilding", uid("mb", bid), EX.project, bid), edge("BuildingToRoot", uid("btr", bid), bid, EX.root),
      edge("BuildingToOperation", uid("bto", bid), bid, EX.op_main));
    F.embodied_root.push(node("EmbodiedRoot", { id: EX.root }), edge("RootToModel", uid("rtm", bid), EX.root, EX.model),
      edge("RootToConstructionProcess", uid("rtcp", bid), EX.root, EX.process));
    F.element_model.push(node("ElementModel", { id: EX.model }), ...SUPER.map(s => edge("ParentTo", uid("pt", s), EX.model, s)));
    F.construction_process.push(node("ConstructionProcess", { id: EX.process }));
    F.operation.push(node("Operation", { id: EX.op_main, electricity_usage: +(en.elGrid / g.gfa).toFixed(3), heat_usage: +(en.dhGrid / g.gfa).toFixed(3), electricity_production: 0 }),
      edge("ElectricitySource", uid("es", bid), EX.op_main, EX.el_source), edge("HeatingSource", uid("hs", bid), EX.op_main, EX.dh_source),
      node("Operation", { id: EX.op_install, electricity_usage: 0, heat_usage: 0, electricity_production: 0.0 }),
      edge("ElectricitySource", uid("es2", bid), EX.op_install, EX.el_source), edge("HeatingSource", uid("hs2", bid), EX.op_install, EX.el_source2));
    const made = {};
    function stageNode(id, mid, label, k, stage, unit, mass, gwp, src, ext, url) {
      F.stages.push(node("Stage", { id, name: { Danish: `CF ${label} (${k})`, English: `CF ${label} (${k})`, German: "" }, comment: "", source: "User",
        locked: true, valid_to: "2030-12-31", stage, stage_unit: unit, indicator_unit: unit, stage_factor: 1.0, mass_factor: mass, indicator_factor: 1.0,
        external_source: src, external_id: ext, external_version: "2025", external_url: url || "", indicators: Object.assign({}, IND0, { GWP: gwp }) }));
    }
    function product(mid) {
      if (made[mid]) return made[mid];
      const m = DB.materials[mid];
      const [unit, mass, gw, conv] = productSpec(mid, DB);
      const pid = uid("product", mid);
      F.products.push(node("Product", { id: pid, name: { Danish: `CF ${m.name_dk || m.label}`.slice(0, 120), English: `CF ${m.label}`, German: "" },
        source: "User", comment: `${m.source} ${m.t7_id || m.uuid || ""}`, locked: true }));
      for (const [k, st] of STAGES) {
        if (Math.abs(gw[k]) < 1e-12 && st !== "A1to3") continue;
        const sid = uid("stage", mid, st);
        stageNode(sid, mid, m.label, k, st, unit, mass, gw[k], m.source || "", m.t7_id || m.uuid || "", m.url);
        F.stages.push(edge("ProductToStage", { id: uid("pts", mid, st), enabled: true }, pid, sid), edge("Generic", uid("sc", mid, st), EX.stage_cat, sid));
      }
      return (made[mid] = [pid, unit, conv]);
    }
    function construction(key, unit, mats, life, qty) {
      const eid = uid("element", key, bid), cid = uid("construction", key, bid), cat = CAT[key];
      F.elements.push(node("Element", { id: eid, name: { Danish: `CF ${key}`, English: `CF ${key}`, German: "" }, source: "User", comment: "", enabled: true, active: true }),
        edge("ElementToConstruction", { id: uid("etc", key, bid), amount: +qty.toFixed(4), enabled: true }, eid, cid));
      F.element_category_edges.push(edge("CategoryToElement", { id: uid("cte", key, bid), enabled: true }, cat, eid));
      F.constructions.push(node("Construction", { id: cid, name: { Danish: `CF ${key}` }, unit, source: "User", comment: "", layer: 1, locked: true }));
      F.constructions_extra.push(edge("CategoryToConstruction", { id: uid("ctc", key, bid), layers: [1] }, cat, cid));
      for (const mid of Object.keys(mats)) {
        const [pid, punit, conv] = product(mid);
        F.constructions.push(edge("ConstructionToProduct", { id: uid("ctp", key, mid, bid), amount: +(mats[mid] * conv).toFixed(6), unit: punit,
          lifespan: life, demolition: false, enabled: true, delayed_start: 0 }, cid, pid));
      }
      return cid;
    }
    for (const c of comps) construction(c.key, unitOf(c.key), c.mats, c.life, c.qty);
    if (d.mode !== "keep") {
      const cid = construction("installations", "M2", {}, 100, g.gfa);
      for (const mid of ["inst_drain", "inst_water", "inst_hvac"]) {
        const m = DB.materials[mid], pid = uid("product", mid);
        F.products.push(node("Product", { id: pid, name: { Danish: `CF ${m.name_dk}`, English: `CF ${m.label}`, German: "" }, source: "User",
          comment: `BR18 standardværdi ${m.t7_id} x ${CF.PERIOD} år`, locked: true }));
        for (const [k, st] of STAGES) {
          const v = (m.gwp[k] || 0) * CF.PERIOD;
          if (Math.abs(v) < 1e-12 && st !== "A1to3") continue;
          const sid = uid("stage", mid, st);
          stageNode(sid, mid, m.label, k, st, "M2", 1.0, v, "BR18 tabel 7 (2025)", m.t7_id, "");
          F.stages.push(edge("ProductToStage", { id: uid("pts", mid, st), enabled: true }, pid, sid), edge("Generic", uid("sc", mid, st), EX.stage_cat, sid));
        }
        F.constructions.push(edge("ConstructionToProduct", { id: uid("ctp", "installations", mid, bid), amount: 1.0, unit: "M2", lifespan: 100,
          demolition: false, enabled: true, delayed_start: 0 }, cid, pid));
      }
    }
    return F;
  }

  /** Recompute an export with LCAbyg's rules (amount x stage factor; replacements = ceil(50/lifespan)-1). */
  function recompute(F) {
    const stages = {}, ps = {}, cp = {}, ec = {};
    for (const lst of Object.values(F)) for (const it of lst) {
      if (it.Node && it.Node.Stage) stages[it.Node.Stage.id] = [it.Node.Stage.stage, it.Node.Stage.indicators.GWP];
      if (it.Edge) {
        const [p, a, b] = it.Edge, kind = Object.keys(p)[0], pay = p[kind];
        if (kind === "ProductToStage") (ps[a] = ps[a] || []).push(b);
        if (kind === "ConstructionToProduct") (cp[a] = cp[a] || []).push([b, pay.amount, pay.lifespan]);
        if (kind === "ElementToConstruction") ec[b] = pay.amount;
      }
    }
    const out = { A1to3: 0, B4: 0, C3C4: 0, D: 0 };
    for (const [cid, qty] of Object.entries(ec)) for (const [pid, amt, life] of cp[cid] || []) {
      const n = Math.max(0, Math.ceil(CF.PERIOD / life) - 1), v = {};
      for (const s of ps[pid] || []) v[stages[s][0]] = stages[s][1];
      const a = qty * amt * (v.A1to3 || 0), c = qty * amt * ((v.C3 || 0) + (v.C4 || 0));
      out.A1to3 += a; out.C3C4 += c; out.B4 += n * (a + c); out.D += qty * amt * (v.D || 0) * (1 + n);
    }
    return out;
  }
  root.LCAbygExport = { build, recompute };
})(typeof self !== "undefined" ? self : this);

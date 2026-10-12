/* CarbonForm engine: parametric apartment block -> quantities -> whole-life carbon (EN 15978, BR18 2025).
 *
 * Pure functions, no DOM. Used live by the web app and, via Playwright, by the Python test suite, which
 * checks it against an independent Python implementation (src/carbon/engine.py).
 *
 * Material data: BR18 annex 2 table 7 (2025) generic dataset (+ ÖKOBAUDAT for green roof and transport).
 * Units: m, m2, m3, kg, kWh, kg CO2e. Reference period 50 years. Results per m2 floor area per year.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.CarbonForm = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const PERIOD = 50;
  const START_YEAR = 2026;

  // BR18 limits from 1 July 2025, kg CO2e / m2 / year
  const LIMITS = { main: 7.5, construction: 1.5, main_2023: 12.0, main_2027: 6.4, main_2029: 5.8 };

  // Danish B6 emission factors 2025-2075 (SBST, Artelia 2023, table 1), kg CO2e/kWh, linear between points
  const EF_YEARS = [2025, 2030, 2035, 2040, 2045, 2050];
  const EF_EL = [0.0801, 0.0325, 0.0291, 0.0285, 0.0261, 0.0248];
  const EF_DH = [0.0418, 0.0181, 0.0140, 0.0134, 0.0132, 0.0132];
  function ef(series, year) {
    if (year <= EF_YEARS[0]) return series[0];
    const last = EF_YEARS.length - 1;
    if (year >= EF_YEARS[last]) return series[last];
    for (let i = 0; i < last; i++) {
      if (year <= EF_YEARS[i + 1]) {
        const t = (year - EF_YEARS[i]) / (EF_YEARS[i + 1] - EF_YEARS[i]);
        return series[i] + t * (series[i + 1] - series[i]);
      }
    }
    return series[last];
  }

  // A4 transport distances (km) and A5 waste rates
  const TRANSPORT_KM = { concrete_c30: 30, concrete_c25: 30, hollowcore: 80, precast_wall20: 80, precast_wall15: 80, stair: 80 };
  const DEFAULT_KM = 150;
  const WASTE = { concrete_c30: 0.02, concrete_c25: 0.02, rebar: 0.03, hollowcore: 0.01, precast_wall20: 0.01,
                  precast_wall15: 0.01, stair: 0.0, door_steel: 0.0 };
  const DEFAULT_WASTE = 0.05;

  const OPTIONS = {
    footprint: ["bar", "L", "U", "courtyard", "tower"],
    structure: ["concrete", "precast", "timber", "steel"],
    facade: ["brick", "wood", "fibrecement", "render"],
    insulation: ["mineralwool", "woodfibre", "eps", "cellulose"],
    windows: ["wood", "woodalu", "pvc", "curtain"],
    roof: ["flat", "green", "pitched"],
    heating: ["district", "heatpump"],
    mode: ["new", "renovate", "keep"],
  };
  const LABELS = {
    concrete: "In-situ concrete", precast: "Precast concrete", timber: "CLT timber", steel: "Steel frame",
    brick: "Brick", wood: "Larch", fibrecement: "Fibre cement", render: "Rendered ETICS",
    mineralwool: "Mineral wool", woodfibre: "Wood fibre", eps: "EPS", cellulose: "Cellulose",
    woodalu: "Wood-alu", pvc: "PVC", curtain: "Curtain wall",
    flat: "Flat (felt)", green: "Green roof", pitched: "Pitched (tiles)", district: "District heating", heatpump: "Heat pump",
    bar: "Bar", L: "L-shape", U: "U-shape", courtyard: "Courtyard", tower: "Tower",
  };

  const DEFAULT_DESIGN = {
    mode: "new", footprint: "bar", length: 48, depth: 13, floors: 5, storeyHeight: 3.0, twist: 0, setback: 0,
    structure: "concrete", facade: "brick", insulation: "mineralwool", windows: "woodalu", wwr: 0.30,
    roof: "flat", pv: 0.0, balconies: true, heating: "district", topUpFloors: 0,
  };

  // ---------------------------------------------------------------- geometry
  function polyArea(p) { let a = 0; for (let i = 0; i < p.length; i++) { const [x1, y1] = p[i], [x2, y2] = p[(i + 1) % p.length]; a += x1 * y2 - x2 * y1; } return Math.abs(a) / 2; }
  function polyPerim(p) { let s = 0; for (let i = 0; i < p.length; i++) { const [x1, y1] = p[i], [x2, y2] = p[(i + 1) % p.length]; s += Math.hypot(x2 - x1, y2 - y1); } return s; }

  /** Footprint outline: {outer:[[x,y]..], holes:[[[x,y]..]]}, axis-aligned, metres. */
  function footprint(d) {
    const L = d.length, D = d.depth;
    switch (d.footprint) {
      case "L": { const W = Math.max(D * 1.5, 0.6 * L); return { outer: [[0, 0], [L, 0], [L, D], [D, D], [D, W], [0, W]], holes: [] }; }
      case "U": { const W = Math.max(D * 1.8, 0.6 * L); return { outer: [[0, 0], [L, 0], [L, W], [L - D, W], [L - D, D], [D, D], [D, W], [0, W]], holes: [] }; }
      case "courtyard": { const W = Math.max(D * 2.6, 0.75 * L); return { outer: [[0, 0], [L, 0], [L, W], [0, W]], holes: [[[D, D], [D, W - D], [L - D, W - D], [L - D, D]]] }; }
      case "tower": { const s = Math.max(D * 1.6, 16); return { outer: [[0, 0], [s, 0], [s, s], [0, s]], holes: [] }; }
      default: return { outer: [[0, 0], [L, 0], [L, D], [0, D]], holes: [] };
    }
  }

  function geometry(d) {
    const fp = footprint(d);
    const area = polyArea(fp.outer) - fp.holes.reduce((s, h) => s + polyArea(h), 0);
    const perim = polyPerim(fp.outer) + fp.holes.reduce((s, h) => s + polyPerim(h), 0);
    const floors = d.floors + (d.mode === "renovate" ? (d.topUpFloors || 0) : 0);
    const topLoss = d.setback > 0 && floors > 1 ? Math.min(area * 0.6, perim * d.setback) : 0;
    const gfa = area * floors - topLoss;
    const wallGross = perim * d.storeyHeight * floors;
    const windowArea = wallGross * d.wwr;
    const wallOpaque = wallGross - windowArea;
    const roofArea = d.roof === "pitched" ? area / Math.cos((35 * Math.PI) / 180) : area;
    const nBalc = d.balconies ? floors * Math.max(1, Math.floor(perim / 2 / 7)) : 0;
    const cores = Math.max(1, Math.ceil(area / 450));
    return { fp, footprintArea: area, perimeter: perim, floors, gfa, wallGross, windowArea, wallOpaque, roofArea, nBalc,
             balconyArea: nBalc * 5.25, cores, heightTotal: floors * d.storeyHeight };
  }

  // ---------------------------------------------------------------- assemblies
  const R_OTHER = 0.4;                                  // m2K/W of the other layers + surface resistances
  const U_NEW = { wall: 0.15, roof: 0.10, ground: 0.10 };
  const U_OLD = { wall: 0.60, roof: 0.40, ground: 0.50, window: 2.8 };   // 1970s Danish block
  const INSUL = { mineralwool: ["mw_facade", "mw_roof"], woodfibre: ["wood_fibre", "wood_fibre"], eps: ["eps", "eps"],
                  cellulose: ["cellulose", "cellulose"] };
  const LAMBDA = { mineralwool: 0.034, woodfibre: 0.040, eps: 0.031, cellulose: 0.039 };

  /** insulation layer for a required thermal resistance R (m2K/W) -> {materialId: quantity per m2} */
  function insulationLayer(kind, R, roof, DB) {
    const id = INSUL[kind][roof ? 1 : 0];
    const m = DB.materials[id];
    if (m.unit === "m2R") return { [id]: R };
    // cellulose is declared per kg: thickness = R * lambda, mass = thickness * density
    return { [id]: R * LAMBDA[kind] * (m.density || 43.75) };
  }
  function thickness(kind, R) { return R * LAMBDA[kind]; }

  const STRUCT = {
    concrete: { slab: { concrete_c30: 0.22, rebar: 19.8 }, intWall: { concrete_c30: 0.18, rebar: 10.8 },
                extBack: { concrete_c30: 0.15, rebar: 9.0 }, roofDeck: { concrete_c30: 0.22, rebar: 19.8 }, found: 1.0 },
    precast:  { slab: { hollowcore: 1, concrete_c25: 0.03 }, intWall: { precast_wall20: 1 }, extBack: { precast_wall15: 1 },
                roofDeck: { hollowcore: 1, concrete_c25: 0.03 }, found: 0.95 },
    timber:   { slab: { clt: 0.16, concrete_c25: 0.04, gypsum: 2 }, intWall: { clt: 0.10, gypsum: 4 },
                extBack: { timber: 0.025, gypsum: 2 }, roofDeck: { clt: 0.14 }, found: 0.6 },
    steel:    { slab: { hollowcore: 1, steel_section: 22, concrete_c25: 0.03 }, intWall: { gypsum: 4, steel_section: 4 },
                extBack: { steel_section: 8, gypsum: 2 }, roofDeck: { hollowcore: 1, steel_section: 10 }, found: 0.85 },
  };
  const CLADDING = {
    brick: { mats: { brick: 194.4, steel_section: 2 }, life: 120 },          // 108 mm x 1800 kg/m3
    wood: { mats: { larch: 0.022, timber: 0.006 }, life: 40 },
    fibrecement: { mats: { fibre_cement: 1, steel_section: 1.5 }, life: 50 },
    render: { mats: { etics_render: 1 }, life: 40 },
  };
  const WINDOWS = {
    wood: { id: "window_wood", life: 40, U: 0.80 },
    woodalu: { id: "window_woodalu", life: 40, U: 0.75 },
    pvc: { id: "window_pvc", life: 30, U: 0.85 },
    curtain: { id: "curtain_wall", life: 40, U: 0.90 },
  };
  const ROOF_FINISH = {
    flat: { mats: { roofing_felt: 1 }, life: 30 },
    green: { mats: { roofing_felt: 1, green_roof: 1 }, life: 40 },
    pitched: { mats: { roof_tiles: 52.5, timber: 0.03 }, life: 60 },
  };

  /** Component list: {key, group, label, qty, unit, mats{id: qtyPerUnit}, life, existing} */
  function components(d, g, DB) {
    const comps = [];
    const reno = d.mode !== "new";
    const add = (key, group, label, qty, unit, mats, life, existing = false) =>
      comps.push({ key, group, label, qty, unit, mats, life, existing });
    const S = reno ? STRUCT.concrete : STRUCT[d.structure];
    const baseFloors = d.floors;
    const k = (S.found || 1) * (baseFloors / 5);
    add("foundation", "foundation", "Strip foundations", g.perimeter, "m", { concrete_c25: 0.5 * k, rebar: 20 * k }, 120, reno);
    add("ground_slab", "foundation", "Ground slab", g.footprintArea, "m2", { concrete_c25: 0.12, rebar: 6 }, 120, reno);
    add("ground_insulation", "foundation", "Ground slab insulation", g.footprintArea, "m2",
        insulationLayer("eps", reno ? 1.5 : 1 / U_NEW.ground - R_OTHER, false, DB), 120, reno);
    add("slabs", "structure", "Floor slabs", g.footprintArea * (baseFloors - 1), "m2", S.slab, 120, reno);
    add("int_walls", "structure", "Load-bearing inner walls", 0.30 * g.footprintArea * baseFloors, "m2", S.intWall, 120, reno);
    add("ext_backing", "structure", "Exterior wall structure", g.wallOpaque * (baseFloors / g.floors), "m2", S.extBack, 120, reno);
    add("roof_deck", "structure", "Roof deck", g.footprintArea, "m2", S.roofDeck, 120, reno);
    add("stairs", "structure", "Stairs", g.cores * baseFloors, "pcs", { stair: 1 }, 120, reno);
    if (d.mode === "renovate" && d.topUpFloors > 0) {
      const T = STRUCT.timber, share = d.topUpFloors / g.floors;
      add("topup_slabs", "structure", "Timber top-up: floors", g.footprintArea * d.topUpFloors, "m2", T.slab, 120);
      add("topup_walls", "structure", "Timber top-up: inner walls", 0.30 * g.footprintArea * d.topUpFloors, "m2", T.intWall, 120);
      add("topup_ext", "structure", "Timber top-up: exterior walls", g.wallOpaque * share, "m2", T.extBack, 120);
      add("topup_stairs", "structure", "Timber top-up: stairs", g.cores * d.topUpFloors, "pcs", { stair: 1 }, 120);
    }
    if (d.mode === "keep") {
      // no renovation, but ordinary maintenance still happens: like-for-like windows and roofing replaced on schedule
      add("maint_windows", "windows", "Window replacement (like-for-like)", g.windowArea, "m2", { window_pvc: 1 }, 30, "maintain");
      add("maint_roof", "roof", "Roofing replacement (like-for-like)", g.roofArea, "m2", { roofing_felt: 1 }, 30, "maintain");
      return comps;
    }
    const Rw = reno ? 1 / U_NEW.wall - 1 / U_OLD.wall : 1 / U_NEW.wall - R_OTHER;
    const Rr = reno ? 1 / U_NEW.roof - 1 / U_OLD.roof : 1 / U_NEW.roof - R_OTHER;
    add("wall_insulation", "facade", `Facade insulation (${Math.round(thickness(d.insulation, Rw) * 1000)} mm)`, g.wallOpaque, "m2",
        insulationLayer(d.insulation, Rw, false, DB), 80);
    add("cladding", "facade", `Cladding: ${LABELS[d.facade]}`, g.wallOpaque, "m2", CLADDING[d.facade].mats, CLADDING[d.facade].life);
    add("windows", "windows", `Windows: ${LABELS[d.windows] || d.windows}`, g.windowArea, "m2", { [WINDOWS[d.windows].id]: 1 }, WINDOWS[d.windows].life);
    add("roof_insulation", "roof", `Roof insulation (${Math.round(thickness(d.insulation, Rr) * 1000)} mm)`, g.footprintArea, "m2",
        insulationLayer(d.insulation, Rr, true, DB), 80);
    add("roof_finish", "roof", `Roof: ${LABELS[d.roof]}`, g.roofArea, "m2", ROOF_FINISH[d.roof].mats, ROOF_FINISH[d.roof].life);
    add("partitions", "interior", "Partitions", (reno ? 0.3 : 1) * g.gfa, "m2", { gypsum: 1.6, timber: 0.002 }, 50);
    add("flooring", "interior", "Floor finishes", (reno ? 0.5 : 1) * g.gfa * 0.85, "m2", { parquet: 1 }, 30);
    add("doors", "interior", "Apartment doors", Math.ceil(g.gfa / 75), "pcs", { door_steel: 1 }, 40);
    if (g.nBalc > 0) add("balconies", "balconies", "Balconies", g.nBalc, "pcs", { precast_wall20: 5.25, steel_section: 30 }, 80);
    if (d.pv > 0 && d.roof !== "green") add("pv", "energy", "Rooftop PV", d.pv * g.footprintArea * 0.6, "m2", { pv: 1 }, 30);
    return comps;
  }

  // ---------------------------------------------------------------- operational energy (screening, not Be18)
  const DEGREE_KH = 100;   // heating-season degree kilo-hours, Danish climate, indoor 20 C
  function energy(d, g) {
    const keep = d.mode === "keep";
    const Uw = keep ? U_OLD.wall : U_NEW.wall, Ur = keep ? U_OLD.roof : U_NEW.roof;
    const Ug = d.mode === "new" ? U_NEW.ground : U_OLD.ground;
    const Uwin = keep ? U_OLD.window : WINDOWS[d.windows].U;
    const Htr = 1.10 * (Uw * g.wallOpaque + Ur * g.footprintArea + 0.5 * Ug * g.footprintArea + Uwin * g.windowArea);
    const mech = keep ? 0.0 : 0.30, hr = 0.85, infil = keep ? 0.50 : 0.10;    // l/s per m2
    const Hve = (mech * (1 - hr) + infil) * 1e-3 * g.gfa * 1200;
    const H = Htr + Hve;
    const loss = H * DEGREE_KH;
    const gains = 20 * g.gfa + 61 * g.windowArea;                              // internal + solar, heating season
    const heat = Math.max(0, loss - 0.8 * gains);
    const dhw = 13 * g.gfa;
    const elBase = (keep ? 3 : 5) * g.gfa;
    const hp = d.heating === "heatpump" && !keep;
    const COP = 3.0;
    const heatDelivered = heat + dhw;
    const elHP = hp ? heatDelivered / COP : 0;
    const pvArea = d.pv > 0 && d.roof !== "green" && !keep ? d.pv * g.footprintArea * 0.6 : 0;
    const pvYield = pvArea * 180;
    const elDemand = elBase + elHP;
    const pvUsed = Math.min(pvYield, elDemand);
    const elGrid = elDemand - pvUsed;
    const dhGrid = hp ? 0 : heatDelivered;
    return { H, Htr, Hve, heat, dhw, elBase, elHP, pvYield, pvUsed, elGrid, dhGrid, pvArea,
             heat_m2: heat / g.gfa, delivered_m2: (elGrid + dhGrid) / g.gfa };
  }
  function b6Series(en) {
    const out = [];
    for (let i = 0; i < PERIOD; i++) { const y = START_YEAR + i; out.push(en.elGrid * ef(EF_EL, y) + en.dhGrid * ef(EF_DH, y)); }
    return out;
  }

  // ---------------------------------------------------------------- LCA
  function gwp(DB, id, mod) {
    const m = DB.materials[id];
    if (!m) throw new Error("unknown material " + id);
    const v = m.gwp[mod];
    return v == null ? 0 : v / (m.per || 1);
  }
  function materialMass(DB, id, q) {
    const m = DB.materials[id];
    if (m.unit === "kg") return q;
    if (m.unit === "m³" || m.unit === "m3") return q * (m.density || 0);
    if (m.unit === "m2R") return q * (m.lambda || 0.035) * (m.density || 30);
    if (m.unit === "stk" || m.unit === "pcs") return q * (m.mass_per_pcs || 0);
    return q * (m.mass_per_m2 || 0);
  }

  function evaluate(design, DB) {
    const d = Object.assign({}, DEFAULT_DESIGN, design || {});
    const g = geometry(d);
    const comps = components(d, g, DB);
    const truck = gwp(DB, "truck", "A4") / 1000;              // kg CO2e per kg.km
    const mods = { A1A3: 0, A4: 0, A5: 0, B4: 0, B6: 0, C3C4: 0, D: 0 };
    const byGroup = {}, byMaterial = {}, events = [], rows = [];
    let instDeferred = 0;
    let mass = 0;
    for (const c of comps) {
      const n = Math.max(0, Math.ceil(PERIOD / c.life) - 1);
      const r = { key: c.key, group: c.group, label: c.label, qty: c.qty, unit: c.unit, life: c.life, n, existing: c.existing,
                  A1A3: 0, A4: 0, A5: 0, B4: 0, C3C4: 0, D: 0, mass: 0, mats: c.mats };
      for (const id of Object.keys(c.mats)) {
        const q = c.mats[id] * c.qty;
        const a13 = q * gwp(DB, id, "A1-A3");
        const c34 = q * (gwp(DB, id, "C3") + gwp(DB, id, "C4"));
        const dd = q * gwp(DB, id, "D");
        const ms = materialMass(DB, id, q);
        r.mass += ms;
        if (c.existing === "maintain") {                     // existing item: only its future replacements count
          r.B4 += n * (a13 + c34); r.A4 += 0; byMaterial[id] = (byMaterial[id] || 0) + n * (a13 + c34); continue;
        }
        if (c.existing) { r.C3C4 += c34; byMaterial[id] = (byMaterial[id] || 0) + c34; continue; }
        const w = WASTE[id] != null ? WASTE[id] : DEFAULT_WASTE;
        r.A1A3 += a13; r.C3C4 += c34; r.D += dd * (1 + n);
        r.A4 += ms * (TRANSPORT_KM[id] || DEFAULT_KM) * truck;
        r.A5 += w * (a13 + c34);
        r.B4 += n * (a13 + c34);
        byMaterial[id] = (byMaterial[id] || 0) + (1 + n) * (a13 + c34);
      }
      for (let i = 1; i <= n; i++) events.push({ year: i * c.life, kg: r.B4 / n });
      mods.A1A3 += r.A1A3; mods.A4 += r.A4; mods.A5 += r.A5; mods.B4 += r.B4; mods.C3C4 += r.C3C4; mods.D += r.D;
      byGroup[c.group] = (byGroup[c.group] || 0) + r.A1A3 + r.B4 + r.C3C4;
      mass += r.mass;
      rows.push(r);
    }
    // technical installations: BR18 standard values (kg CO2e/m2/yr). Counted in every scenario: an unrenovated
    // building also renews its heating, water and ventilation systems within 50 years.
    {
      const inst = { key: "installations", group: "installations", label: "Technical installations (BR18 standard values)",
                     qty: g.gfa, unit: "m2", life: PERIOD, n: 0, existing: false, A1A3: 0, A4: 0, A5: 0, B4: 0, C3C4: 0, D: 0, mass: 0, mats: {} };
      for (const id of ["inst_drain", "inst_water", "inst_hvac"]) {
        inst.A1A3 += g.gfa * PERIOD * gwp(DB, id, "A1-A3");
        inst.C3C4 += g.gfa * PERIOD * (gwp(DB, id, "C3") + gwp(DB, id, "C4"));
        inst.D += g.gfa * PERIOD * gwp(DB, id, "D");
        inst.mats[id] = 1;
      }
      mods.A1A3 += inst.A1A3; mods.C3C4 += inst.C3C4; mods.D += inst.D;
      if (d.mode === "keep") instDeferred = inst.A1A3;            // an old block renews its systems mid-life, not on day one
      byGroup.installations = inst.A1A3 + inst.C3C4;
      rows.push(inst);
    }
    // site processes (A5): 15 kWh electricity + 1.2 l diesel per m2 of new / renovated floor area
    const siteArea = d.mode === "new" ? g.gfa : d.mode === "renovate" ? 0.35 * g.gfa : 0;
    mods.A5 += siteArea * (15 * ef(EF_EL, START_YEAR) + 1.2 * 2.7);
    const en = energy(d, g);
    const b6 = b6Series(en);
    mods.B6 = b6.reduce((s, v) => s + v, 0);
    byGroup.operation = mods.B6;
    const denom = g.gfa * PERIOD;
    const main = (mods.A1A3 + mods.B4 + mods.B6 + mods.C3C4) / denom;
    const constr = (mods.A4 + mods.A5) / denom;
    const timeline = [mods.A1A3 + mods.A4 + mods.A5 - instDeferred];
    for (let i = 0; i < PERIOD; i++) {
      let v = timeline[i] + b6[i];
      if (i + 1 === 25) v += instDeferred;
      for (const e of events) if (e.year === i + 1) v += e.kg;
      if (i === PERIOD - 1) v += mods.C3C4;
      timeline.push(v);
    }
    return {
      design: d, geometry: g, components: rows, energy: en, b6, modules: mods, byGroup, byMaterial, mass,
      perM2Yr: { A1A3: mods.A1A3 / denom, A4: mods.A4 / denom, A5: mods.A5 / denom, B4: mods.B4 / denom,
                 B6: mods.B6 / denom, C3C4: mods.C3C4 / denom, D: mods.D / denom },
      total: main, construction: constr, upfront_m2: (mods.A1A3 + mods.A4 + mods.A5) / g.gfa,
      limits: LIMITS, pass: main <= LIMITS.main, passConstruction: constr <= LIMITS.construction,
      tonnes: (mods.A1A3 + mods.A4 + mods.A5 + mods.B4 + mods.B6 + mods.C3C4) / 1000, timeline,
    };
  }

  /** Same site, three futures: keep the 1970s block, renovate it, or demolish and build the design new. */
  function scenarios(design, DB) {
    const d = Object.assign({}, DEFAULT_DESIGN, design || {});
    const keep = evaluate(Object.assign({}, d, { mode: "keep", topUpFloors: 0 }), DB);
    const reno = evaluate(Object.assign({}, d, { mode: "renovate" }), DB);
    const fresh = evaluate(Object.assign({}, d, { mode: "new" }), DB);
    // demolishing the existing block releases its end-of-life emissions at year 0
    const demolition = keep.modules.C3C4;
    const newTimeline = fresh.timeline.map(v => v + demolition);
    const cross = (a, b) => { for (let i = 0; i < a.length; i++) if (a[i] <= b[i] && i > 0) return i; return null; };
    return { keep, renovate: reno, newBuild: fresh, demolition,
             timelines: { keep: keep.timeline, renovate: reno.timeline, newBuild: newTimeline },
             breakEvenRenovateVsKeep: cross(reno.timeline, keep.timeline),
             breakEvenNewVsKeep: cross(newTimeline, keep.timeline) };
  }

  /** Exhaustive search over the discrete material choices (geometry fixed). */
  function optimise(design, DB, opts) {
    const base = Object.assign({}, DEFAULT_DESIGN, design || {});
    const keys = (opts && opts.keys) || ["structure", "facade", "insulation", "windows", "roof", "heating"];
    const pvChoices = (opts && opts.pv) || [0, 0.6];
    let best = null, n = 0;
    const rec = (i, cur) => {
      if (i === keys.length) {
        for (const pv of pvChoices) {
          const dd = Object.assign({}, cur, { pv });
          const r = evaluate(dd, DB); n++;
          const score = r.total + 0.25 * Math.max(0, r.construction - LIMITS.construction);
          if (!best || score < best.score) best = { score, design: dd, result: r };
        }
        return;
      }
      for (const v of OPTIONS[keys[i]]) rec(i + 1, Object.assign({}, cur, { [keys[i]]: v }));
    };
    rec(0, base);
    best.evaluated = n;
    return best;
  }

  return { evaluate, scenarios, optimise, geometry, footprint, components, energy, ef, insulationLayer,
           EF_EL, EF_DH, EF_YEARS, LIMITS, OPTIONS, LABELS, DEFAULT_DESIGN, PERIOD, START_YEAR, U_NEW, U_OLD, R_OTHER };
});

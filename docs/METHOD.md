# CarbonForm: method

CarbonForm is a **design-stage screening tool**. It follows the structure of a Danish BR18 LCA (EN 15978 modules,
50 years, per m² floor area) so options can be compared early. It is **not** a BR18 submission; use LCAbyg (or another
approved tool) with project-specific quantities and EPDs for that. The LCAbyg export (below) is the bridge.

## 1. Rules (BR18, from 1 July 2025)

| Item | Value | Source |
|---|---|---|
| Limit, multi-storey housing (A1–A3, B4, B6, C3–C4) | **7.5** kg CO₂e/m²/yr | BR18 §298 (2025) |
| Limit, construction process (A4–A5) | **1.5** kg CO₂e/m²/yr | BR18 (2025) |
| Previous general limit (shown for reference) | 12.0 | BR18 (2023) |
| Announced tightening (shown as gauge ticks) | ≈ 6.4 (2027), ≈ 5.8 (2029) | announced reduction path (approximate) |
| Reference period | 50 years | BR18 |
| Module D | reported, not counted in the limit | BR18 |

## 2. Data

* **Materials: BR18 annex 2, table 7 (2025)**, the generic dataset that the Danish building regulations prescribe
  (`tabel-7-2025.xlsx`, bygningsreglementet.dk). 33 of the 35 datasets come from it: Danish generic data, industry EPDs
  (CLT, glulam, structural timber, hollow-core and wall elements) and generic data. Each dataset in `data/materials.json`
  keeps its table 7 sorting ID (e.g. `#B1318` CLT).
* **Technical installations:** BR18 table 7 **standard values** for multi-storey housing (#S0007 drainage, #S0008 water,
  #S0009 heating/ventilation/cooling), kg CO₂e per m² per year.
* **Supplementary (not in table 7):** extensive green roof and truck transport factor from **ÖKOBAUDAT 2024-II**
  (free for building LCA calculations).
* **Operational energy factors (B6):** SBST / Artelia (2023), *Emissionsfaktorer – El, fjernvarme og ledningsgas
  2025–2075*, table 1. Electricity 0.0801 (2025) → 0.0248 kg/kWh (2050–75); district heating 0.0418 → 0.0132.
  Linear interpolation between the published years.

## 3. Geometry → quantities

Footprints: bar, L, U, courtyard (with inner facade), tower, set by length and wing depth. Storeys × storey height give
gross wall area. Window area = window ratio × gross wall area. Optional top-floor setback and per-storey twist (the twist is visual;
areas are unchanged).

| Component | Quantity basis | Assembly per unit (examples) | Life |
|---|---|---|---|
| Strip foundations | perimeter (m) | C25/30 concrete 0.5 m³/m + rebar 20 kg/m, scaled by storeys and structure weight | 120 |
| Ground slab | footprint | 0.12 m³ concrete + 6 kg rebar, EPS for U = 0.10 | 120 |
| Floor slabs | footprint × (storeys − 1) | concrete 0.22 m³ + 19.8 kg rebar / hollow-core 22 cm / CLT 0.16 m³ + 40 mm topping / hollow-core + 22 kg steel | 120 |
| Load-bearing inner walls | 0.30 m² per m² floor | concrete 18 cm / precast 20 cm / CLT 10 cm / gypsum + steel studs | 120 |
| Exterior wall structure | opaque wall | concrete 15 cm / precast 15 cm / timber frame / steel frame | 120 |
| Facade insulation | opaque wall | thermal resistance for **U = 0.15** (R = 1/U − 0.4); table 7 insulation is declared per m² at R = 1 | 80 |
| Cladding | opaque wall | brick 108 mm · larch 22 mm · fibre-cement board · ETICS render | 120 · 40 · 50 · 40 |
| Windows | window area | table 7 complete windows (timber, timber-alu, PVC) or curtain wall | 40 (PVC 30) |
| Roof insulation / finish | footprint / roof area | R for U = 0.10; felt · felt + green roof · clay tiles | 80 / 30 · 40 · 60 |
| Stairs | cores × storeys | concrete stair per storey (1 core per 450 m² footprint) | 120 |
| Partitions, floors, doors | floor area | 1.6 m² gypsum board per m²; multi-layer parquet; 1 steel apartment door per 75 m² | 50 · 30 · 40 |
| Balconies | per balcony (one per 7 m of long facade) | 5.25 m² precast element + 30 kg steel | 80 |
| PV | 60 % of roof × cover ratio | monocrystalline panel | 30 |
| Installations | floor area | BR18 standard values × 50 years | n/a |

## 4. Life-cycle modules

* **A1–A3** = Σ quantity × table 7 value.
* **B4 replacements**: n = ⌈50 / life⌉ − 1 per component (LCAbyg convention); each replacement adds A1–A3 + C3–C4.
* **C3–C4** at end of life; **D** reported separately (excluded from the limit).
* **Biogenic carbon** follows EN 15804+A2 as encoded in table 7: timber shows negative A1–A3 (uptake) and a matching
  C3 release (incineration).
* **A4** = mass × distance (30 km ready-mix, 80 km precast, 150 km other) × 0.111 kg CO₂e/t·km (truck, ÖKOBAUDAT).
* **A5** = waste (2 % concrete, 1 % precast, 3 % rebar, 5 % other) × (A1–A3 + C3–C4) + site energy (15 kWh electricity
  + 1.2 l diesel per m² of new/renovated floor area).

## 5. Operational energy (screening, not Be18)

Heat-loss coefficient H = 1.10 × Σ U·A (10 % thermal bridges) + ventilation (0.30 l/s/m², 85 % heat recovery) +
infiltration (0.10 l/s/m²). Heating = H × 100 kKh − 0.8 × (20 kWh/m² internal + 61 kWh/m² window solar gains).
Hot water 13 kWh/m²; building electricity 5 kWh/m². Heat pump: COP 3. PV: 180 kWh/m² panel, credited up to the
building's own electricity use. New build gives ≈ 17 kWh/m² heating; the unrenovated 1970s block (U 0.6/0.4/2.8,
natural ventilation 0.5 l/s/m²) gives ≈ 130 kWh/m². **This is a screening estimate**: a BR18 project uses Be18.

## 6. Renovation scenarios

* **Keep:** the 1970s concrete block stays as is, with like-for-like window and roofing replacement (30 years) and renewal of
  installations (BR18 standard values, placed at year 25 in the timeline). Existing structure has no production impact.
* **Renovate:** existing structure kept. New: insulation from U = 0.6 → 0.15 (wall) and 0.4 → 0.10 (roof), cladding,
  windows, roofing, 30 % new partitions, 50 % new floors, installations, optional timber top-up storeys.
* **Demolish + new:** the end-of-life impact of the existing block is added at year 0.

## 7. Verification

* **Two independent implementations** (JavaScript in the browser, Python for reports/export) agree to 1e-9 on 300
  random designs, including the full 50-year curve.
* **Hand checks:** footprint areas/perimeters (incl. the courtyard's inner facade), replacement rule, official emission factors,
  insulation resistance, BR18 installation standard values.
* **LCAbyg round trip:** exported projects, recomputed with LCAbyg's rules (amount × stage factor, replacements from
  lifespan), reproduce the engine's A1–A3, B4, C3–C4 and D exactly (40 random designs).
* **Plausibility:** heating demand 8–35 kWh/m² (new) and 90–180 kWh/m² (1970s); concrete/brick lands near the 2025 limit.

## 8. Known limits

* Quantities are parametric estimates, not a takeoff: no basements, lift shafts, cores, interior finishes beyond
  floors, or façade details. Use LCAbyg/BIM quantities for a real project.
* Generic data only; EPDs of the chosen products will differ.
* Operational energy is a steady-state screening model, not Be18.
* PV is credited only against the building's own electricity (no export credit), which, with Denmark's low-carbon grid
  factors, makes rooftop PV a net carbon increase in this method. That is a real consequence of the BR18 rules and factors.

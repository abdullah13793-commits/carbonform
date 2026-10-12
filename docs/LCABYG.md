# Opening a CarbonForm design in LCAbyg

CarbonForm exports a project in the **LCAbyg 5 JSON format** (the format of the official LCAbyg JSON guide and
`import_example`). The export contains:

* `building.json`: building node (floor area, storeys, 50-year period, BR2018), linked to the project
* `elements.json` + `element_category_edges.json`: one element per CarbonForm component, placed in LCAbyg's own
  element categories (Ydervægge, Etagedæk, Tage, Vinduer, Randfundamenter, … gen_dk IDs)
* `constructions.json` + `constructions_extra.json`: one construction per component with its products and lifespans
* `products.json` + `stages.json`: the BR18 table 7 data used by CarbonForm, as user products with stages
  A1–A3, C3, C4, D (insulation converted from "per m² at R = 1" to kg)
* `operation.json`: electricity and district-heating use in kWh/m²/yr

## Import (LCAbyg 2023 desktop, free download from lcabyg.dk → Previous versions)

1. In CarbonForm, click **Export to LCAbyg**. This downloads `carbonform_lcabyg.zip`. Or run
   `python src/lcabyg_export.py my_design.json exports/my_project`.
2. Unzip. Copy the folder next to LCAbyg's own `import_example` (LCAbyg 5 installation folder).
3. In LCAbyg: **File → Import → JSON** and select the folder.
4. Run the calculation. LCAbyg 2023 reports against the **BR18 2023** rules (limit 12). CarbonForm also shows the 2025
   limit (7.5) and the separate A4–A5 limit.

## What to expect

The embodied totals (A1–A3, B4, C3–C4) should match CarbonForm. The test suite verifies this by re-reading every export
with LCAbyg's rules. Operational energy (B6) can differ because LCAbyg 2023 uses the 2023 emission factors; CarbonForm
uses the 2025–2075 factors. Only the official LCAbyg run is valid for a building permit.

> The export was built against the published JSON guide and verified by round-trip recalculation. It has not yet been
> opened in a licensed LCAbyg installation on this machine, so the first import is the final check.

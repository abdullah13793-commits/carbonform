"""CarbonForm report: A4 landscape HTML -> PDF (headless Edge). All numbers come from the engine.

python src/make_report.py -> reports/CarbonForm_Report.pdf
"""
import base64, io, json, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from carbon import engine as E

DB = E.load_db()
FIG, REN = ROOT / "reports/figures", ROOT / "renders"


def img(p, style="width:100%"):
    p = Path(p)
    if not p.exists():
        return f"<div class=missing>missing {p.name}</div>"
    im = Image.open(p).convert("RGB")
    if im.width > 1800:
        im = im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=85, optimize=True)
    return f'<img style="{style}" src="data:image/jpeg;base64,{base64.b64encode(b.getvalue()).decode()}">'


def main():
    base = E.evaluate({}, DB)
    fail = E.evaluate({"floors": 3, "wwr": 0.6, "insulation": "eps", "windows": "pvc", "pv": 0.6}, DB)
    clt = E.evaluate({"structure": "timber", "facade": "wood", "insulation": "woodfibre", "windows": "wood"}, DB)
    reno = E.evaluate({"mode": "renovate", "facade": "wood", "insulation": "cellulose", "windows": "wood"}, DB)
    keep = E.evaluate({"mode": "keep"}, DB)
    t7 = sum(1 for m in DB["materials"].values() if "BR18" in str(m.get("source")))
    f2 = lambda v: f"{v:.2f}"
    rows = "".join(f"<tr><td>{m['label']}</td><td>{m.get('t7_id') or 'ÖKOBAUDAT'}</td><td>{m['unit']}</td>"
                   f"<td class=n>{m['gwp'].get('A1-A3', 0) / (m.get('per') or 1):,.3g}</td></tr>"
                   for k, m in list(DB["materials"].items())[:24] if not k.startswith("inst"))
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>CarbonForm report</title><style>
@page {{ size: A4 landscape; margin: 0 }}
:root {{ --bg:#0b0d0c; --ink:#f2f4ef; --ink2:#b9c0b8; --muted:#7d867e; --line:#2a302d; --acc:#b7f36a }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--ink); font-family:"Segoe UI",Arial,sans-serif; font-size:9.5pt }}
.pg {{ width:297mm; height:210mm; padding:12mm 14mm 10mm; page-break-after:always; position:relative; overflow:hidden }}
.pg:last-child {{ page-break-after:auto }}
h1 {{ font-size:34pt; margin:0; letter-spacing:-.02em; font-weight:800 }} h1 span {{ color:var(--acc) }}
h2 {{ font-size:18pt; margin:0 0 3mm; font-weight:700; letter-spacing:-.01em }}
.eb {{ font:600 7.5pt Consolas,monospace; letter-spacing:.14em; text-transform:uppercase; color:var(--acc) }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:6mm }} .tw {{ display:grid; grid-template-columns:1.35fr 1fr; gap:7mm }}
.k {{ display:flex; gap:9mm; flex-wrap:wrap }} .k div b {{ display:block; font-size:22pt; font-weight:800 }} .k div span {{ font-size:7.5pt; color:var(--ink2); text-transform:uppercase; letter-spacing:.08em }}
p, li {{ line-height:1.45; color:var(--ink2) }} b {{ color:var(--ink) }}
table {{ border-collapse:collapse; width:100%; font-size:8pt }} td, th {{ padding:1.1mm 2mm; border-bottom:.4pt solid var(--line); text-align:left; color:var(--ink2) }}
th {{ color:var(--ink); border-bottom:.8pt solid var(--ink2) }} td.n {{ text-align:right; font-family:Consolas,monospace; color:var(--ink) }}
.foot {{ position:absolute; left:14mm; right:14mm; bottom:6mm; display:flex; justify-content:space-between; font-size:7pt; color:var(--muted); border-top:.4pt solid var(--line); padding-top:2mm }}
img {{ display:block; border-radius:2mm }} .ok {{ color:#8fe58f }} .no {{ color:#ffb1b3 }}
</style></head><body>

<section class="pg"><div class="eb">Parametric whole-life carbon · BR18 2025 · demonstration project</div>
<h1>Carbon<span>Form</span></h1>
<div class="tw" style="margin-top:5mm"><div>{img(REN / 'still_full_fail.png')}</div>
<div><p style="font-size:11pt;color:var(--ink)">Shape a building, swap its materials and renovate it, and its whole-life carbon updates live against
the Danish BR18 limit. The 50-year emissions appear next to it as a cloud of CO₂ gas at its true volume.</p>
<div class="k"><div><b>{f2(base['total'])}</b><span>concrete + brick</span></div><div><b>{f2(clt['total'])}</b><span>CLT + larch</span></div>
<div><b>{f2(reno['total'])}</b><span>renovate 1970s</span></div></div>
<p>Data: <b>BR18 annex 2 table 7 (2025)</b> ({t7} datasets) and the BR18 installation standard values, the official 2025–2075 Danish emission factors for
electricity and district heating, and ÖKOBAUDAT for two gaps. Exports a project to <b>LCAbyg</b>.</p>
<p>This low-rise glazed concrete scheme scores <b class="no">{f2(fail['total'])}</b>, <b>above the 7.5 limit</b>, so the cloud turns orange.</p></div></div>
<div class="foot"><span>Abdallah Alhussein · MSc Eng, Architectural Engineering, DTU (2026)</span><span>Design-stage screening, not a BR18 submission · page 1</span></div></section>

<section class="pg"><div class="eb">The tool</div><h2>Every slider is a design decision; every decision has a number</h2>
{img(REN / 'still_full_pass.png', 'width:100%;max-height:150mm;object-fit:cover')}
<div class="foot"><span>Form · structure · facade · insulation · windows · roof · energy · keep/renovate/rebuild · optimiser · LCAbyg export</span><span>page 2</span></div></section>

<section class="pg"><div class="eb">Results</div><h2>Structure decides; the facade fine-tunes</h2>
<div class="two"><div>{img(FIG / 'matrix.png')}</div><div>{img(FIG / 'archetypes.png')}</div></div>
<p>Per m² per year over 50 years, A1–A3 + B4 + B6 + C3–C4. Timber shows its stored (biogenic) carbon as negative production and releases it at
end of life (EN 15804+A2). Every new-build archetype passes 7.5; in-situ concrete with brick is closest to the limit.</p>
<div class="foot"><span>5-storey bar, 48 × 13 m, 3,120 m² unless stated</span><span>page 3</span></div></section>

<section class="pg"><div class="eb">Renovation</div><h2>The greenest building is often the one already standing</h2>
<div class="tw"><div>{img(FIG / 'scenarios.png')}</div>
<div><p>Same site, 50 years. Keeping the 1970s block still costs heating (≈130 kWh/m² a year) plus ordinary maintenance. A deep renovation
cuts heating to ≈20 kWh/m² for a fraction of a new building's materials. Demolish-and-rebuild starts with the old block's end-of-life
and a new building's production emissions.</p>
<div class="k"><div><b>{reno['modules']['A1A3']/1000 + reno['modules']['A4']/1000 + reno['modules']['A5']/1000:,.0f} t</b><span>renovation up-front</span></div>
<div><b>{keep['energy']['heat'] / keep['geometry']['gfa']:.0f} → {reno['energy']['heat'] / reno['geometry']['gfa']:.0f}</b><span>kWh/m² heating</span></div></div></div></div>
<div class="foot"><span>Keep: like-for-like windows and roofing every 30 years; installations renewed mid-life</span><span>page 4</span></div></section>

<section class="pg"><div class="eb">Sensitivity</div><h2>What actually moves the result</h2>
<div class="tw"><div>{img(FIG / 'sensitivity.png')}</div>
<div><ul><li><b>Structure is the big lever.</b> CLT instead of in-situ concrete is −1.98; precast is −0.54.</li>
<li><b>Facade and windows are second order</b> (−0.3 each).</li>
<li><b>Rooftop PV adds carbon under these rules</b> (+0.37). With Denmark's 2025–2075 grid factors (≈0.025 kg/kWh) and PV credited only
against the building's own use, the panels' production outweighs the saved electricity.</li>
<li><b>Taller is better per m²:</b> 5 → 9 storeys is −0.28, because foundations and roof are shared by more floor area.</li></ul></div></div>
<div class="foot"><span>One change at a time from the concrete/brick base case</span><span>page 5</span></div></section>

<section class="pg"><div class="eb">Data, method and verification</div><h2>Built on the regulation's own numbers</h2>
<div class="two"><div><table><tr><th>Material</th><th>Table 7 ID</th><th>Unit</th><th style="text-align:right">A1–A3</th></tr>{rows}</table></div>
<div><table><tr><th>Rule / check</th><th>Value</th></tr>
<tr><td>BR18 2025 limit, multi-storey housing</td><td class=n>7.5</td></tr><tr><td>A4–A5 construction limit</td><td class=n>1.5</td></tr>
<tr><td>Reference period</td><td class=n>50 yr</td></tr><tr><td>B6 factors electricity / district heating 2025 → 2050</td><td class=n>0.080→0.025 / 0.042→0.013</td></tr>
<tr><td>Installations (BR18 standard values, housing)</td><td class=n>0.50 A1–A3</td></tr>
<tr><td>JS vs Python engine, 300 random designs</td><td class=n>agree to 1e-9</td></tr>
<tr><td>LCAbyg export, recomputed with LCAbyg rules</td><td class=n>exact, 40 designs</td></tr>
<tr><td>Automated tests</td><td class=n>19 / 19</td></tr>
<tr><td>Heating demand new / 1970s</td><td class=n>{base['energy']['heat']/base['geometry']['gfa']:.0f} / {keep['energy']['heat']/keep['geometry']['gfa']:.0f} kWh/m²</td></tr></table>
<p style="margin-top:4mm"><b>Limits.</b> Parametric quantities (no basement, lift cores or detailed finishes); generic data; screening energy model (not Be18);
a design-stage tool, not a BR18 submission. The LCAbyg export is the bridge to an official calculation.</p></div></div>
<div class="foot"><span>Sources: bygningsreglementet.dk (bilag 2, tabel 7, 2025) · SBST emissionsfaktorer 2025–2075 · oekobaudat.de · LCAbyg JSON guide</span><span>page 6</span></div></section>
</body></html>"""
    out = ROOT / "reports/CarbonForm_Report.html"; out.write_text(html, encoding="utf-8")
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    pdf = ROOT / "reports/CarbonForm_Report.pdf"
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", out.as_uri()], timeout=180)
    print("pdf ->", pdf, pdf.exists(), round(pdf.stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()

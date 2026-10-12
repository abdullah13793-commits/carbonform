"""Assemble the single-file web app: web/template.html + engine.js + lcabyg_export.js + materials.json -> docs/index.html

python src/build_web.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    t = (ROOT / "web/template.html").read_text(encoding="utf-8")
    eng = (ROOT / "src/engine.js").read_text(encoding="utf-8")
    exp = (ROOT / "src/lcabyg_export.js").read_text(encoding="utf-8")
    db = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8"))
    t = t.replace("/*__ENGINE__*/", eng).replace("/*__EXPORT__*/", exp).replace("/*__DB__*/null", json.dumps(db, ensure_ascii=False))
    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    (out / "index.html").write_text(t, encoding="utf-8")
    print("->", out / "index.html", round(len(t) / 1024), "KB")


if __name__ == "__main__":
    main()

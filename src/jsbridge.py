"""Run src/engine.js inside headless Edge (Playwright) so Python tests can call the exact web engine."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class JSEngine:
    def __enter__(self):
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch(channel="msedge", headless=True)
        self.page = self._b.new_page()
        self.page.set_content("<html><body></body></html>")
        self.page.add_script_tag(content=(ROOT / "src/engine.js").read_text(encoding="utf-8"))
        db = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8"))
        self.page.evaluate("db => { window.DB = db; }", db)
        return self

    def evaluate(self, design):
        return self.page.evaluate("d => CarbonForm.evaluate(d, window.DB)", design)

    def optimise(self, design, opts=None):
        return self.page.evaluate("([d, o]) => { const r = CarbonForm.optimise(d, window.DB, o); return {design: r.design, total: r.result.total, evaluated: r.evaluated}; }", [design, opts])

    def call(self, expr, arg=None):
        return self.page.evaluate(expr, arg)

    def __exit__(self, *a):
        self._b.close(); self._pw.stop()

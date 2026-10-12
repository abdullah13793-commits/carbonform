"""Screenshot the web app with headless Edge (WebGL via SwiftShader). python src/shoot.py [out.png] [w] [h] [js...]"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def shoot(out, w=1600, h=900, actions=(), wait=4.0, url=None):
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        errs = []
        pg.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        pg.goto(url or (ROOT / "docs/index.html").as_uri())
        pg.wait_for_function("window.CFApp !== undefined", timeout=60000)
        for a in actions:
            if isinstance(a, (int, float)):
                time.sleep(a)
            else:
                pg.evaluate(a)
        time.sleep(wait)
        pg.screenshot(path=out)
        b.close()
    return errs


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "renders/web_test.png")
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 1600
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    errs = shoot(out, w, h, actions=sys.argv[4:])
    print("\n".join(errs) or "no console errors"); print("->", out)

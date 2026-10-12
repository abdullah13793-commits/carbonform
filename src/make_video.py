"""Record the CarbonForm story deterministically (fixed time step, every frame rendered) and encode MP4.

python src/make_video.py full    -> publish/carbonform_story_1080p.mp4   (1920x1080, dashboard visible)
python src/make_video.py cinema  -> publish/carbonform_story_4x5.mp4     (1080x1350, LinkedIn feed)
python src/make_video.py hq      -> publish/carbonform_story_4k.mp4      (3840x2160, dashboard text readable after re-encoding)
python src/make_video.py still <out.png> <w> <h> <json-design> [cinema]    -> single frame
"""
import json, subprocess, sys, time
from pathlib import Path
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FPS = 30

# (design patch or "OPT", caption template, seconds). {total} and {tonnes} are filled from the live result.
STORY = [
    ({"mode": "new", "footprint": "bar", "structure": "concrete", "facade": "brick", "insulation": "eps", "windows": "pvc",
      "roof": "flat", "pv": 0, "heating": "district", "floors": 5, "twist": 0, "setback": 0, "length": 48, "balconies": True, "topUpFloors": 0},
     "A concrete and brick apartment block: {total} kg CO₂e/m²/yr", 4.2),
    (None, "Its 50-year emissions as gas, to scale: {tonnes} t CO₂ is a {diam} m sphere", 4.2),
    ({"floors": 9, "footprint": "U", "length": 56}, "Make it bigger and the cloud grows with it", 4.0),
    ({"structure": "timber", "facade": "wood", "insulation": "woodfibre", "windows": "wood"},
     "CLT, larch and wood fibre: {total} kg CO₂e/m²/yr", 4.4),
    ({"footprint": "bar", "floors": 6, "length": 48, "twist": 3, "setback": 1.5}, "Twist it, set back the top floor", 3.6),
    ({"roof": "flat", "pv": 0.9, "heating": "heatpump"}, "Add rooftop PV and a heat pump", 3.6),
    ({"mode": "keep", "twist": 0, "setback": 0, "pv": 0}, "Or keep the old 1970s block as it is", 3.8),
    ({"mode": "renovate", "facade": "wood", "insulation": "cellulose", "windows": "wood", "topUpFloors": 2},
     "Renovate it and add two timber storeys: {total}", 4.4),
    ("OPT", "The optimiser tries every combination: best {total} kg CO₂e/m²/yr", 4.6),
    (None, "CarbonForm · BR18 2025 data · exports to LCAbyg", 3.6),
]


def run(mode, out):
    # hq: 1600x900 CSS layout at 2.4x pixel density -> 3840x2160 frames, larger and sharper dashboard text
    w, h, dpr = {"full": (1920, 1080, 1), "hq": (1600, 900, 2.4)}.get(mode, (1080, 1350, 1))
    frames_dir = ROOT / f"renders/frames_{mode}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for p in frames_dir.glob("*.jpg"):
        p.unlink()
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="msedge", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=dpr)
        pg.goto((ROOT / "docs/index.html").as_uri())
        pg.wait_for_function("window.CFApp !== undefined", timeout=60000)
        pg.evaluate("document.fonts.ready")
        cinema = mode == "cinema"
        pg.evaluate(f"CFApp.layout('{'cinema' if cinema else 'full'}'); CFApp.startCapture(); CFApp.setRotateSpeed(1.1)")
        pg.evaluate("CFApp.orbit(0.5, 0.28); CFApp.frame(%s, true)" % ("0.70" if cinema else "0.82"))
        n = 0
        t0 = time.time()
        for patch, cap, secs in STORY:
            if patch == "OPT":
                pg.evaluate("(() => { const b = CarbonForm.optimise(Object.assign({}, CFApp.design, {mode:'new', topUpFloors:0}), DB); CFApp.set(b.design); })()")
            elif patch:
                pg.evaluate("p => CFApp.set(p)", patch)
            r = pg.evaluate("({t: CFApp.result.total, tonnes: CFApp.result.tonnes})")
            diam = 2 * (3 * r["tonnes"] * 1000 / 1.87 / (4 * 3.14159265)) ** (1 / 3)
            text = cap.format(total=f"{r['t']:.2f}", tonnes=f"{r['tonnes']:,.0f}", diam=f"{diam:.0f}")
            pg.evaluate("s => CFApp.setCaption(s)", text)
            for i in range(int(secs * FPS)):
                pg.evaluate(f"CFApp.captureStep({1 / FPS})")
                pg.screenshot(path=str(frames_dir / f"{n:05d}.jpg"), type="jpeg", quality=92)
                n += 1
            print(f"  segment done: {text}  ({n} frames, {time.time() - t0:.0f}s)", flush=True)
        b.close()
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-framerate", str(FPS), "-i", str(frames_dir / "%05d.jpg"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18" if mode == "hq" else "21", "-preset", "slow", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    print("video ->", out, round(Path(out).stat().st_size / 1e6, 1), "MB")


def still(out, w, h, design, cinema=False, zoom=0.82, az=0.5, el=0.30, warm=90):
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="msedge", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg.goto((ROOT / "docs/index.html").as_uri())
        pg.wait_for_function("window.CFApp !== undefined", timeout=60000)
        pg.evaluate("document.fonts.ready")
        pg.evaluate(f"CFApp.layout('{'cinema' if cinema else 'full'}'); CFApp.startCapture(); CFApp.autorotate(false)")
        pg.evaluate("p => CFApp.set(p)", design)
        pg.evaluate(f"CFApp.orbit({az}, {el}); CFApp.frame({zoom}, true)")
        for _ in range(warm):
            pg.evaluate("CFApp.captureStep(1/30)")
        pg.evaluate(f"CFApp.orbit({az}, {el}); CFApp.frame({zoom}, true); CFApp.captureStep(1/30)")
        pg.screenshot(path=out)
        b.close()


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "still":
        still(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), json.loads(sys.argv[5]), len(sys.argv) > 6 and sys.argv[6] == "cinema")
    else:
        out = ROOT / {"full": "publish/carbonform_story_1080p.mp4", "hq": "publish/carbonform_story_4k.mp4"}.get(m, "publish/carbonform_story_4x5.mp4")
        out.parent.mkdir(exist_ok=True)
        run(m, out)

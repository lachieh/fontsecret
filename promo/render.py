"""Render the social videos in promo/index.html to MP4, one browser screenshot per frame.

    uv run --with playwright python promo/render.py            # all videos -> promo/out/*.mp4
    uv run --with playwright python promo/render.py a --stills 0 60 120 179   # PNG frames only

Chrome shapes the text with HarfBuzz, so the dots come from the patched font itself.
"""

import argparse
import functools
import http.server
import subprocess
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FPS, FRAMES, W, H = 30, 195, 1080, 1350


def serve() -> int:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(HERE))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="*", default=["a", "b", "c"])
    ap.add_argument("--stills", nargs="*", type=int)
    ap.add_argument("--suffix", default="", help="appended to output names, so earlier renders are kept")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    port = serve()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for v in args.videos:
            page.goto(f"http://127.0.0.1:{port}/index.html?v={v}")
            page.evaluate("window.ready")
            if args.stills is not None:
                for f in args.stills:
                    page.evaluate(f"window.render({f})")
                    page.screenshot(path=OUT / f"{v}-{f:03d}.png")
                continue
            mp4 = OUT / f"fontsecret-{v}{args.suffix}.mp4"
            ff = subprocess.Popen(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                 "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                 "-movflags", "+faststart", str(mp4)],
                stdin=subprocess.PIPE)
            for f in range(FRAMES):
                page.evaluate(f"window.render({f})")
                ff.stdin.write(page.screenshot(type="png"))
            ff.stdin.close()
            ff.wait()
            page.evaluate(f"window.render({FRAMES - 1})")
            page.screenshot(path=OUT / f"fontsecret-{v}{args.suffix}-poster.png")
            print(mp4)
        browser.close()


if __name__ == "__main__":
    main()

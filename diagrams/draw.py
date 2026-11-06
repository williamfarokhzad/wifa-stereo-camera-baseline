"""Regenerate the WebP diagrams. Requires Pillow and DejaVu Sans fonts."""
from pathlib import Path
import sys
from fractions import Fraction as F
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from baseline import audit_mount, bounds, read_design

INK, MUTED = "#132c3c", "#365665"
BLUE, RED, TEAL = "#205496", "#a3343c", "#006b59"
PAPER, GRID = "#f6fbfc", "#d5e4e7"


def font(size, bold=False):
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)


def canvas(title, subtitle):
    image = Image.new("RGB", (1000, 590), PAPER)
    dr = ImageDraw.Draw(image)
    dr.text((50, 34), title, font=font(39, True), fill=INK)
    dr.text((52, 96), subtitle, font=font(24), fill=MUTED)
    return image, dr


def save(im, name):
    im.save(HERE / name, "WEBP", lossless=True, method=6)


def geometry():
    im, dr = canvas("Two cameras, one point", "Top view of an ideal rectified pair · not to scale")
    a, b, p = (310, 452), (690, 452), (575, 196)
    dr.line((a, (310, 150)), fill=GRID, width=4)
    dr.line((b, (690, 150)), fill=GRID, width=4)
    dr.line((a, p), fill=BLUE, width=6)
    dr.line((b, p), fill=TEAL, width=6)
    dr.line((p, (860, 196)), fill=GRID, width=3)
    dr.line(((800, 196), (800, 452)), fill=INK, width=3)
    for y in (196, 452):
        dr.line(((787, y), (813, y)), fill=INK, width=3)
    dr.text((822, 302), "Depth Z", font=font(24, True), fill=INK)
    for x, y in (a, b, p):
        dr.ellipse((x-10, y-10, x+10, y+10), fill=INK)
    dr.text((p[0], 146), "Scene point", anchor="mt", font=font(26, True), fill=INK)
    dr.text((a[0], 484), "Left center", anchor="mt", font=font(24), fill=BLUE)
    dr.text((b[0], 484), "Right center", anchor="mt", font=font(24), fill=TEAL)
    dr.line(((310, 538), (690, 538)), fill=INK, width=3)
    for x in (310, 690):
        dr.line(((x, 528), (x, 548)), fill=INK, width=3)
    dr.text((500, 549), "Baseline B", anchor="mt", font=font(26, True), fill=INK)
    save(im, "stereo-baseline-geometry.webp")


def limits():
    d = read_design(HERE.parent / "examples/narrow-window.json")
    lo, _, hi = bounds(d)
    im, dr = canvas("Only a narrow window fits", "800 px focal length · 0.5 to 3 m working depth")
    x = lambda b: 100 + 800 * (float(b) - 75) / 30
    y = 285
    dr.rectangle((x(lo), 230, x(hi), 355), fill="#c2e9db")
    dr.line(((x(75), y), (x(105), y)), fill=INK, width=4)
    for n in range(75, 106, 5):
        dr.line(((x(n), y-12), (x(n), y+13)), fill=INK, width=3)
        dr.text((x(n), y-55), str(n), anchor="mt", font=font(24), fill=INK)
    dr.text((500, 161), "Baseline in mm", anchor="mt", font=font(24, True), fill=INK)
    for b in d.mounts_mm:
        _, _, _, failures = audit_mount(d, b)
        c = RED if failures else TEAL
        dr.ellipse((x(b)-9, y-9, x(b)+9, y+9), fill=c)
        dr.line(((x(b), y+13), (x(b), 392)), fill=c, width=3)
    for b, title, outcome, pos, c in (
        (F(80), "80 mm", "Far error too high", 218, RED),
        (F(96), "96 mm", "Passes all limits", 622, TEAL),
        (F(100), "100 mm", "Near disparity too high", 832, RED),
    ):
        dr.line(((x(b), 392), (pos, 410)), fill=c, width=3)
        dr.text((pos, 424), title, anchor="mt", font=font(29, True), fill=c)
        dr.text((pos, 465), outcome, anchor="mt", font=font(20), fill=INK)
    dr.text((500, 537), f"Modeled feasible window: {float(lo):.3f} to {float(hi):.3f} mm",
            anchor="mt", font=font(25, True), fill=TEAL)
    save(im, "stereo-baseline-window.webp")


if __name__ == "__main__":
    geometry()
    limits()

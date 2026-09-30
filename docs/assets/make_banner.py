"""Render the repo banner / social preview (1280x640) — a stylised utility network.

Run: python docs/assets/make_banner.py   (writes social-preview.png and banner.png)
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 2  # supersample
W, H = 1280 * S, 640 * S
OUT = Path(__file__).parent
F = "/usr/share/fonts/opentype/noto/NotoSansCJK-{}.ttc"


def font(weight, size):
    return ImageFont.truetype(F.format(weight), size * S, index=0)


BG_TOP, BG_BOT = (9, 20, 36), (14, 34, 58)
LINE = (56, 118, 168)
ACCENT = (0, 188, 212)       # teal
ACCENT2 = (255, 179, 71)     # amber (source / controller)
TEXT = (236, 242, 248)
MUTED = (150, 172, 196)

img = Image.new("RGB", (W, H), BG_TOP)
d = ImageDraw.Draw(img)
for y in range(H):
    t = y / H
    d.line([(0, y), (W, y)], fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))

# --- network on the right: source -> feeders -> branches (radial tree) -------
random.seed(7)
net = Image.new("RGBA", (W, H), (0, 0, 0, 0))
nd = ImageDraw.Draw(net)
src = (int(W * 0.81), int(H * 0.50))
edges, nodes = [], []


def grow(p, ang, length, depth):
    if depth == 0:
        return
    q = (p[0] + length * math.cos(ang), p[1] + length * math.sin(ang))
    edges.append((p, q, depth))
    nodes.append((q, depth))
    kids = 2 if depth > 1 else random.choice([1, 2])
    for k in range(kids):
        spread = 0.55 if kids == 2 else 0
        grow(q, ang + (k - (kids - 1) / 2) * spread * 2 + random.uniform(-0.15, 0.15),
             length * random.uniform(0.62, 0.78), depth - 1)


for a in range(6):
    grow(src, a * math.pi / 3 + 0.3, 138 * S, 4)

for p, q, depth in edges:
    w = max(1, depth) * S
    nd.line([p, q], fill=LINE + (110 + depth * 30,), width=w)
for (x, y), depth in nodes:
    r = (3 + depth) * S
    col = ACCENT if depth > 1 else (120, 200, 220)
    nd.ellipse([x - r, y - r, x + r, y + r], fill=col + (235,))
# highlighted trace path (downstream)
path = [src]
p = src
for (a, b, dep) in edges:
    if a == p and len(path) < 5:
        path.append(b)
        p = b
nd.line(path, fill=ACCENT2 + (255,), width=5 * S)
glow = net.filter(ImageFilter.GaussianBlur(6 * S))
img.paste(glow, (0, 0), glow)
img.paste(net, (0, 0), net)
d = ImageDraw.Draw(img)
r = 16 * S
d.ellipse([src[0] - r, src[1] - r, src[0] + r, src[1] + r], fill=ACCENT2, outline=TEXT, width=3 * S)

# fade network under the text column
fade = Image.new("L", (W, H), 0)
fd = ImageDraw.Draw(fade)
for x in range(int(W * 0.64)):
    a = 255 if x < W * 0.52 else int(255 * (1 - (x - W * 0.52) / (W * 0.12)))
    fd.line([(x, 0), (x, H)], fill=a)
bgcopy = Image.new("RGB", (W, H))
bd = ImageDraw.Draw(bgcopy)
for y in range(H):
    t = y / H
    bd.line([(0, y), (W, y)], fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))
img.paste(bgcopy, (0, 0), fade)
d = ImageDraw.Draw(img)

# --- text --------------------------------------------------------------------
x0 = 72 * S
d.text((x0, 92 * S), "ESRI ARCGIS", font=font("Bold", 22), fill=ACCENT)
d.text((x0, 124 * S), "Utility Network", font=font("Black", 76), fill=TEXT)
d.text((x0, 222 * S), "Claude Skill", font=font("Medium", 38), fill=TEXT)
d.text((x0, 284 * S), "Expert UN knowledge for Claude — tracing, subnetworks,",
       font=font("Regular", 22), fill=MUTED)
d.text((x0, 316 * S), "dirty areas, asset packages, versions and every API surface.",
       font=font("Regular", 22), fill=MUTED)

chips = ["Pro", "REST", "JavaScript", "C# SDK", "arcpy", "Migration"]
cx, cy = x0, 392 * S
cf = font("Medium", 20)
for c in chips:
    tw = d.textlength(c, font=cf)
    bw = tw + 36 * S
    d.rounded_rectangle([cx, cy, cx + bw, cy + 44 * S], radius=22 * S,
                        outline=ACCENT, width=2 * S, fill=(12, 40, 64))
    d.text((cx + 18 * S, cy + 8 * S), c, font=cf, fill=TEXT)
    cx += bw + 12 * S

d.text((x0, 540 * S), "github.com/sgdev279/esri-utility-network-skill",
       font=font("Regular", 20), fill=MUTED)
d.rectangle([0, H - 8 * S, W, H], fill=ACCENT)

final = img.resize((1280, 640), Image.LANCZOS)
final.save(OUT / "social-preview.png", optimize=True)
final.crop((0, 60, 1280, 500)).save(OUT / "banner.png", optimize=True)
print("wrote", OUT / "social-preview.png", OUT / "banner.png")

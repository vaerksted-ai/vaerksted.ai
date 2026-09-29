"""Render the brand kit into brand/ (the medallion logo, the wordmark, a lockup
and the GitHub social-preview card) and the site's own icons and link-share
image (favicon.svg/.ico, apple-touch-icon.png, icon-*.png, og-image.png/.svg) — as SVG (text outlined, no font
dependencies) and PNG.

Usage:
    python3 render_brand.py FONT_DIR

FONT_DIR must hold the static TTFs Google Fonts serves for the site's faces:
    sg.ttf     Space Grotesk SemiBold (600)
    runic.ttf  Noto Sans Runic Regular
    jbm.ttf    JetBrains Mono Medium (500)
(Grab the URLs from https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600&family=Noto+Sans+Runic&family=JetBrains+Mono:wght@500
requested with a legacy User-Agent so it answers with .ttf links.)

Requires fonttools and playwright (Chromium) for the PNG renders.
"""
import math
import os
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "brand")
FONT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fonts")

# ─── Palette (mirrors the :root tokens in index.html) ─────────────────────
VOID, PANEL, FROST, MIST = "#07080D", "#0E1018", "#EDEFF3", "#8B939F"
GOLD = "#E8C879"
BIFROST = [(0, "#F26D6D"), (22, "#F2A33C"), (44, "#4FD08A"),
           (64, "#38C5E0"), (82, "#5B8DEF"), (100, "#B07CF6")]
GOLD_METAL = [(0, "#F7E7B0"), (38, "#E6C56F"), (52, "#B8893A"),
              (72, "#EBD083"), (100, "#F7E7B0")]
FUTHARK = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛟᛞ"
VAERKSTED_RUNES = "ᚹᚨᚱᚲᛊᛏᛖᛞ"


# ─── Glyph outlining ──────────────────────────────────────────────────────
class Face:
    def __init__(self, path):
        self.font = TTFont(path)
        self.upm = self.font["head"].unitsPerEm
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.hmtx = self.font["hmtx"]

    def advance(self, ch):
        return self.hmtx[self.cmap[ord(ch)]][0]

    def glyph_path(self, ch, x, y, size):
        """SVG path data for ch with its origin at (x, baseline y), in px."""
        s = size / self.upm
        pen = SVGPathPen(self.glyphs)
        self.glyphs[self.cmap[ord(ch)]].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
        return pen.getCommands()

    def bounds(self, ch):
        pen = BoundsPen(self.glyphs)
        self.glyphs[self.cmap[ord(ch)]].draw(pen)
        return pen.bounds  # xMin, yMin, xMax, yMax in font units (y up)

    def text_width(self, text, size, tracking=0.0):
        s = size / self.upm
        return sum(self.advance(c) * s + tracking * size for c in text) - tracking * size

    def run(self, text, x, y, size, tracking=0.0):
        """Outline a run of text. Returns (path data, x after last glyph)."""
        s = size / self.upm
        parts = []
        for c in text:
            if c != " ":
                parts.append(self.glyph_path(c, x, y, size))
            x += self.advance(c) * s + tracking * size
        return " ".join(parts), x - tracking * size


def stops(spec):
    return "".join(f'<stop offset="{o}%" stop-color="{c}"/>' for o, c in spec)


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ─── Building blocks ──────────────────────────────────────────────────────
def cosmos_defs(w, h, uid):
    return f"""
    <radialGradient id="{uid}cosmos" gradientUnits="userSpaceOnUse" cx="{w/2}" cy="{-h*0.2}" r="{max(w, h)*1.05}">
      <stop offset="0%" stop-color="#1A1733"/><stop offset="40%" stop-color="#0C0B1A"/><stop offset="75%" stop-color="{VOID}"/>
    </radialGradient>"""


def starfield(w, h, n, seed):
    """Deterministic sprinkle of frost and gold stars."""
    import random
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        r = rnd.choice([0.7, 0.9, 1.1, 1.4, 1.8]) * max(w, h) / 1200
        col = GOLD if i % 5 == 0 else FROST
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{col}" opacity="{f(rnd.uniform(0.25, 0.8))}"/>')
    return "\n    ".join(out)


def medallion(sg, runic, cx, cy, R, uid, disc=True, runes=True):
    """The Værksted seal: gold rim, turning rune ring, Bifröst æ.

    R is the outer rim radius. Everything scales from it. runes=False gives the
    simplified seal for favicons, where the rune band would only be noise."""
    k = R / 440.0
    g = []
    g.append(f"""
    <defs>
      <linearGradient id="{uid}gold" gradientUnits="userSpaceOnUse" x1="0" y1="{f(cy-R)}" x2="0" y2="{f(cy+R)}">{stops(GOLD_METAL)}</linearGradient>
      <radialGradient id="{uid}disc" gradientUnits="userSpaceOnUse" cx="{f(cx)}" cy="{f(cy-R*0.55)}" r="{f(R*1.5)}">
        <stop offset="0%" stop-color="#1C1938"/><stop offset="55%" stop-color="{PANEL}"/><stop offset="100%" stop-color="{VOID}"/>
      </radialGradient>
      <radialGradient id="{uid}halo" gradientUnits="userSpaceOnUse" cx="{f(cx)}" cy="{f(cy)}" r="{f(R*0.62)}">
        <stop offset="0%" stop-color="#5B8DEF" stop-opacity="0.22"/><stop offset="60%" stop-color="#B07CF6" stop-opacity="0.07"/><stop offset="100%" stop-color="#B07CF6" stop-opacity="0"/>
      </radialGradient>
    </defs>""")
    if disc:
        g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R+6*k)}" fill="url(#{uid}disc)"/>')
    g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R*0.62)}" fill="url(#{uid}halo)"/>')
    if not runes:
        g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="none" stroke="url(#{uid}gold)" stroke-width="{f(40*k)}"/>')
    else:
        # Rims — same vocabulary as the hero's rune ring
        g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R)}" fill="none" stroke="url(#{uid}gold)" stroke-width="{f(12*k)}"/>')
        g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R-26*k)}" fill="none" stroke="{GOLD}" stroke-width="{f(7*k)}" '
                 f'stroke-dasharray="{f(2*k)} {f(17*k)}" stroke-linecap="round" opacity="0.45"/>')
        g.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(R-116*k)}" fill="none" stroke="url(#{uid}gold)" stroke-width="{f(3*k)}" opacity="0.8"/>')

        # Elder Futhark around the band, glyphs standing on a circle
        size = 48 * k
        base_r = R - 104 * k  # baseline radius (glyph tops point outward)
        s = size / runic.upm
        glyphs = []
        for i, ch in enumerate(FUTHARK):
            ang = 360 * i / len(FUTHARK)
            w = runic.advance(ch) * s
            d = runic.glyph_path(ch, cx - w / 2, cy - base_r, size)
            glyphs.append(f'<path transform="rotate({f(ang)} {f(cx)} {f(cy)})" d="{d}"/>')
        g.append(f'<g fill="{GOLD}" opacity="0.85">{"".join(glyphs)}</g>')

    # æ — centred on its ink box, painted with the Bifröst
    ae_size = (520 if runes else 700) * k
    xmin, ymin, xmax, ymax = sg.bounds("æ")
    sc = ae_size / sg.upm
    ink_w, ink_h = (xmax - xmin) * sc, (ymax - ymin) * sc
    ox = cx - ink_w / 2 - xmin * sc
    base = cy + ink_h / 2 + ymin * sc
    x0, x1 = cx - ink_w / 2, cx + ink_w / 2
    g.append(f"""<defs><linearGradient id="{uid}bifrost" gradientUnits="userSpaceOnUse"
        x1="{f(x0)}" y1="{f(cy - ink_w*0.09)}" x2="{f(x1)}" y2="{f(cy + ink_w*0.09)}">{stops(BIFROST)}</linearGradient></defs>""")
    g.append(f'<path fill="url(#{uid}bifrost)" d="{sg.glyph_path("æ", ox, base, ae_size)}"/>')
    return "\n  ".join(g)


def wordmark(sg, x, baseline, size, uid, gold_fill=None, ae_fill=None):
    """'Værksted' as on the site: gold metal, Bifröst æ, -0.05em tracking."""
    tr = -0.05
    v, x_after_v = sg.run("V", x, baseline, size, tr)
    x_ae = x_after_v + tr * size
    ae, x_after_ae = sg.run("æ", x_ae, baseline, size, tr)
    rest, x_end = sg.run("rksted", x_after_ae + tr * size, baseline, size, tr)
    cap = size * 0.70
    defs = f"""<defs>
      <linearGradient id="{uid}wgold" gradientUnits="userSpaceOnUse" x1="0" y1="{f(baseline - cap*1.05)}" x2="0" y2="{f(baseline + size*0.05)}">{stops(GOLD_METAL)}</linearGradient>
      <linearGradient id="{uid}wbif" gradientUnits="userSpaceOnUse" x1="{f(x_ae)}" y1="{f(baseline-cap)}" x2="{f(x_after_ae)}" y2="{f(baseline)}">{stops(BIFROST)}</linearGradient>
    </defs>"""
    gf = gold_fill or f"url(#{uid}wgold)"
    af = ae_fill or f"url(#{uid}wbif)"
    body = (f'<path fill="{gf}" d="{v} {rest}"/>'
            f'<path fill="{af}" d="{ae}"/>')
    return defs + body, x_end


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{label}">\n  {body}\n</svg>\n')


# ─── Assets ───────────────────────────────────────────────────────────────
def build(sg, runic, jbm):
    assets = {}

    # 1. Avatar — full-bleed square, safe for circle and rounded-square crops.
    S = 1024
    body = [f"<defs>{cosmos_defs(S, S, 'a')}</defs>",
            f'<rect width="{S}" height="{S}" fill="url(#acosmos)"/>',
            f"<g>{starfield(S, S, 40, 7)}</g>",
            medallion(sg, runic, S / 2, S / 2, 440, "a", disc=True)]
    assets["logo-avatar"] = (svg(S, S, "\n  ".join(body), "Værksted"), S, S, False)

    # 2. Seal on transparent — for placing on your own backgrounds.
    body = medallion(sg, runic, S / 2, S / 2, 500, "t", disc=True)
    assets["logo-seal"] = (svg(S, S, body, "Værksted"), S, S, True)

    # 3. Wordmark on transparent.
    size = 200
    pad = 24
    wm, x_end = wordmark(sg, pad, pad + size * 0.72, size, "w")
    W, H = math.ceil(x_end + pad), math.ceil(pad * 2 + size * 0.76)
    assets["logo-wordmark"] = (svg(W, H, wm, "Værksted"), W, H, True)

    # 4. Horizontal lockup: seal + wordmark + runes, on transparent.
    H = 360
    R = 160
    cx = cy = H / 2
    seal = medallion(sg, runic, cx, cy, R, "l", disc=True)
    size = 170
    wx = cx + R + 70
    base = cy + size * 0.18
    wm, x_end = wordmark(sg, wx, base, size, "l")
    runes, _ = runic.run(VAERKSTED_RUNES, wx + 6, base + 62, 34, tracking=0.5)
    W = math.ceil(max(x_end, wx) + 40)
    body = f'{seal}\n  {wm}\n  <path fill="{GOLD}" opacity="0.75" d="{runes}"/>'
    assets["logo-lockup"] = (svg(W, H, body, "Værksted"), W, H, True)

    # 5. GitHub social preview (1280×640, keep content inside a 40px margin).
    W, H = 1280, 640
    grid = (f'<pattern id="sgrid" width="64" height="64" patternUnits="userSpaceOnUse">'
            f'<path d="M 64 0 L 0 0 0 64" fill="none" stroke="{GOLD}" stroke-opacity="0.06" stroke-width="1"/></pattern>'
            f'<linearGradient id="sfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#fff"/>'
            f'<stop offset="80%" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<mask id="smask"><rect width="{W}" height="{H}" fill="url(#sfade)"/></mask>')
    R = 210
    cx, cy = 80 + R, H / 2
    seal = medallion(sg, runic, cx, cy, R, "s", disc=True)
    wx = cx + R + 80
    size = 150
    eyebrow_y = 232
    eyebrow, e_end = jbm.run("AI-NATIVE PRODUCTS & CONSULTING", wx + 52, eyebrow_y, 20, tracking=0.14)
    base = eyebrow_y + 40 + size * 0.70
    wm, x_end = wordmark(sg, wx - 6, base, size, "s")
    runes, _ = runic.run(VAERKSTED_RUNES, wx, base + 62, 30, tracking=0.5)
    url, _ = jbm.run("vaerksted.ai", wx, base + 128, 24, tracking=0.02)
    body = f"""<defs>{cosmos_defs(W, H, 's')}{grid}
    <linearGradient id="sline" x1="0" y1="0" x2="1" y2="0">{stops(BIFROST)}</linearGradient></defs>
  <rect width="{W}" height="{H}" fill="url(#scosmos)"/>
  <rect width="{W}" height="{H}" fill="url(#sgrid)" mask="url(#smask)"/>
  <g>{starfield(W, H, 60, 11)}</g>
  {seal}
  <rect x="{wx}" y="{eyebrow_y - 8}" width="36" height="2.5" fill="url(#sline)"/>
  <path fill="{GOLD}" d="{eyebrow}"/>
  {wm}
  <path fill="{GOLD}" opacity="0.75" d="{runes}"/>
  <path fill="{MIST}" d="{url}"/>"""
    assert x_end < W - 40 and e_end < W - 40, (x_end, e_end)
    assets["social-preview"] = (svg(W, H, body, "Værksted — AI-native products & consulting"), W, H, False)

    # 6. Link-share image (Open Graph / Twitter card, 1200×630) for the site.
    W, H = 1200, 630
    R = 200
    cx, cy = 64 + R, H / 2
    seal = medallion(sg, runic, cx, cy, R, "o", disc=True)
    wx = cx + R + 64
    size = 132
    eyebrow_y = 170
    eyebrow, e_end = jbm.run("AI-NATIVE PRODUCTS & CONSULTING", wx + 50, eyebrow_y, 18, tracking=0.14)
    base = eyebrow_y + 34 + size * 0.70
    wm, x_end = wordmark(sg, wx - 5, base, size, "o")
    tag1, t1_end = sg.run("We build AI-native products,", wx, base + 78, 34, tracking=-0.01)
    tag2, t2_end = sg.run("and help others build them too.", wx, base + 122, 34, tracking=-0.01)
    url, _ = jbm.run("vaerksted.ai", wx, base + 186, 20, tracking=0.08)
    body = f"""<defs>{cosmos_defs(W, H, 'o')}{grid.replace('sgrid', 'ogrid').replace('sfade', 'ofade').replace('smask', 'omask')}
    <linearGradient id="oline" x1="0" y1="0" x2="1" y2="0">{stops(BIFROST)}</linearGradient></defs>
  <rect width="{W}" height="{H}" fill="url(#ocosmos)"/>
  <rect width="{W}" height="{H}" fill="url(#ogrid)" mask="url(#omask)"/>
  <g>{starfield(W, H, 60, 13)}</g>
  {seal}
  <rect x="{wx}" y="{eyebrow_y - 7}" width="34" height="2.5" fill="url(#oline)"/>
  <path fill="{GOLD}" d="{eyebrow}"/>
  {wm}
  <path fill="{FROST}" d="{tag1} {tag2}"/>
  <path fill="{MIST}" d="{url}"/>"""
    assert max(x_end, e_end, t1_end, t2_end) < W - 40, (x_end, e_end, t1_end, t2_end)
    assets["og-image"] = (svg(W, H, body, "Værksted — we build AI-native products, and help others build them too."), W, H, False)
    return assets


def site_icons(sg, runic):
    """The site's favicon family, from the same seal.

    Returns {name: (svg, size, transparent)}. Large icons carry the rune band;
    the small ones use the simplified seal so the æ stays legible."""
    icons = {}
    S = 512
    full = lambda R, uid: (f"<defs>{cosmos_defs(S, S, uid)}</defs>"
                           f'<rect width="{S}" height="{S}" fill="url(#{uid}cosmos)"/>'
                           + medallion(sg, runic, S / 2, S / 2, R, uid))
    icons["icon"] = (svg(S, S, full(220, "i"), "Værksted"), S, False)
    # Maskable: the seal inside the 80% safe zone so launchers can crop freely.
    icons["icon-maskable"] = (svg(S, S, full(190, "m"), "Værksted"), S, False)
    icons["favicon"] = (svg(64, 64, medallion(sg, runic, 32, 32, 29, "f", runes=False), "Værksted"), 64, True)
    return icons


def render_png(page, svg_text, w, h, transparent, out_path):
    page.set_viewport_size({"width": w, "height": h})
    bg = "transparent" if transparent else VOID
    page.set_content(f'<html><body style="margin:0;background:{bg}">{svg_text}</body></html>')
    page.screenshot(path=out_path, omit_background=transparent,
                    clip={"x": 0, "y": 0, "width": w, "height": h})


def main():
    sg = Face(os.path.join(FONT_DIR, "sg.ttf"))
    runic = Face(os.path.join(FONT_DIR, "runic.ttf"))
    jbm = Face(os.path.join(FONT_DIR, "jbm.ttf"))
    os.makedirs(OUT, exist_ok=True)
    assets = build(sg, runic, jbm)
    for name, (text, *_rest) in assets.items():
        if name == "og-image":
            continue
        with open(os.path.join(OUT, f"{name}.svg"), "w") as fh:
            fh.write(text)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        # CHROMIUM lets you point at a system Chromium when the Playwright build is absent.
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        page = browser.new_page()
        for name, (text, w, h, transparent) in assets.items():
            if name == "og-image":
                continue
            render_png(page, text, w, h, transparent, os.path.join(OUT, f"{name}.png"))
        # Site icons go to the repo root, where index.html and the manifest look.
        icons = site_icons(sg, runic)
        icon_svg, _, _ = icons["icon"]
        for px, name in ((512, "icon-512"), (192, "icon-192"), (180, "apple-touch-icon")):
            scaled = icon_svg.replace('width="512" height="512"', f'width="{px}" height="{px}"', 1)
            render_png(page, scaled, px, px, False, os.path.join(HERE, f"{name}.png"))
        render_png(page, icons["icon-maskable"][0], 512, 512, False, os.path.join(HERE, "icon-maskable-512.png"))
        fav_svg = icons["favicon"][0]
        with open(os.path.join(HERE, "favicon.svg"), "w") as fh:
            fh.write(fav_svg)
        fav_png = os.path.join(OUT, "_favicon-256.png")
        render_png(page, fav_svg.replace('width="64" height="64"', 'width="256" height="256"', 1),
                   256, 256, True, fav_png)
        # The link-share image is served from the root as /og-image.png.
        text, w, h, transparent = assets["og-image"]
        render_png(page, text, w, h, transparent, os.path.join(HERE, "og-image.png"))
        with open(os.path.join(HERE, "og-image.svg"), "w") as fh:
            fh.write(text)
        # Smaller avatar sizes some platforms ask for.
        avatar = assets["logo-avatar"][0]
        for px in (500, 400, 200):
            scaled = avatar.replace('width="1024" height="1024"', f'width="{px}" height="{px}"', 1)
            render_png(page, scaled, px, px, False, os.path.join(OUT, f"logo-avatar-{px}.png"))
        browser.close()

    from PIL import Image
    fav = Image.open(fav_png)
    fav.save(os.path.join(HERE, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    os.remove(fav_png)
    print("Brand kit rendered to", OUT)


if __name__ == "__main__":
    main()

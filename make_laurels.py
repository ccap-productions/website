#!/usr/bin/env python3
"""
make_laurels.py
Generates festival laurels for CCAP Productions by replacing the text in
'sample laurel.png' while keeping the original wreath artwork completely intact.

Run from the website directory:
    python3 make_laurels.py

Output: ./laurels/*.png  (one file per festival)
"""

from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
import numpy as np
import os, sys

# ── FONTS (Windows fonts accessible from WSL) ─────────────────────
FONT_NAME = '/mnt/c/Windows/Fonts/arialbd.ttf'   # Arial Bold  – festival name
FONT_SANS = '/mnt/c/Windows/Fonts/segoeui.ttf'   # Segoe UI   – label + year

_font_cache = {}
def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except (IOError, OSError):
            fb = {
                FONT_NAME: '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                FONT_SANS: '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            }.get(path, path)
            print(f'  ⚠  {os.path.basename(path)} not found — using DejaVu fallback')
            _font_cache[key] = ImageFont.truetype(fb, size)
    return _font_cache[key]


# ── TEXT HELPERS ──────────────────────────────────────────────────
def tw(draw, text, f):
    bb = draw.textbbox((0,0), text, font=f); return bb[2]-bb[0]
def th(draw, text, f):
    bb = draw.textbbox((0,0), text, font=f); return bb[3]-bb[1]

def draw_centered(draw, cx, y, text, f, fill):
    draw.text((cx - tw(draw, text, f)//2, y), text, font=f, fill=fill)

def draw_tracked(draw, cx, y, text, f, fill, tracking):
    """Centred text with per-character extra spacing."""
    chars  = list(text)
    widths = [tw(draw, c, f) for c in chars]
    total  = sum(widths) + tracking * max(0, len(chars)-1)
    x = cx - total//2
    for c, w in zip(chars, widths):
        draw.text((x, y), c, font=f, fill=fill)
        x += w + tracking

def best_name_size(draw, line1, line2, max_w, hi=64, lo=24):
    """Largest Arial Bold size where both lines fit within max_w."""
    for size in range(hi, lo-1, -1):
        f = font(FONT_NAME, size)
        lines = [l for l in (line1, line2) if l]
        if all(tw(draw, l, f) <= max_w for l in lines):
            return size
    return lo


# ── CONNECTED-COMPONENT TEXT MASK ─────────────────────────────────
# The key insight: all wreath leaf/branch pixels are connected (via other
# black pixels) to the outer regions of the image. The original text pixels
# ("Cannes Film Festival" etc.) are isolated clusters in the centre.
#
# We label all connected components of black pixels. Any component that has
# at least one pixel OUTSIDE the inner text zone belongs to the wreath.
# Everything else is original text to erase.
#
# Text zone (generous rectangle that contains only text, not leaves):
TEXT_ZONE = (108, 82, 488, 320)   # (x0, y0, x1, y1)

def build_text_mask(sample_arr):
    """
    Returns a boolean H×W array: True = original text pixel (safe to erase).
    Wreath pixels are preserved regardless of position.

    Two-pass strategy:
    1. Use a STRICT threshold (solid black only) to classify connected
       components as leaf or text via connectivity to outside the text zone.
    2. Expand the text mask to also cover ANTI-ALIASED grey halos by
       including any non-white pixel inside the text zone that neighbours
       a confirmed text pixel (dilate by 2 px). Leaf anti-aliasing is
       protected because leaf components are anchored outside the zone.
    """
    x0, y0, x1, y1 = TEXT_ZONE

    # ── Pass 1: classify solid-black pixels ──────────────────────────
    solid = sample_arr[:,:,:3].min(axis=2) < 50    # only near-black

    struct = ndimage.generate_binary_structure(2, 2)   # 8-connected
    labeled, n_labels = ndimage.label(solid, structure=struct)

    leaf_set = set()
    for lbl in range(1, n_labels + 1):
        ys, xs = np.where(labeled == lbl)
        if xs.min() < x0 or xs.max() >= x1 or ys.min() < y0 or ys.max() >= y1:
            leaf_set.add(lbl)

    leaf_solid = np.isin(labeled, list(leaf_set))
    text_solid = solid & ~leaf_solid   # solid text pixels

    # ── Pass 2: grow text mask to include anti-aliased grey halos ────
    # Dilate the solid-text mask by 2 pixels, then intersect with:
    #   - non-white pixels (value < 250 in any channel)
    #   - pixels NOT belonging to a solid leaf component
    dilated    = ndimage.binary_dilation(text_solid, iterations=2)
    non_white  = sample_arr[:,:,:3].min(axis=2) < 250
    text_halo  = dilated & non_white & ~leaf_solid

    return text_solid | text_halo


# ── LAYOUT CONSTANTS (measured from the 595×395 sample) ──────────
#
#  "OFFICIAL SELECTION" : y = 92..115  →  centre y ≈ 103
#  "Cannes Film"        : y = 137..184 →  centre y ≈ 160   \
#  "Festival"           : y = 220..266 →  centre y ≈ 243   /  block centre ≈ 202
#  "2026"               : y = 289..312 →  centre y ≈ 300
#
#  Arial Bold 23pt fills "OFFICIAL SELECTION" to 244 px with tracking=0
#  → label width exactly matches sample with zero extra tracking.
#  Year uses same font, slightly smaller, minimal tracking.

LABEL_CY      = 103    # vertical centre of label row
NAME_BLOCK_CY = 202    # vertical centre of the 2-line name block
YEAR_CY       = 300    # vertical centre of year row

NAME_MAX_W    = 350    # max px per name line (fits up to "Documentary Award" at ~37pt)
LABEL_SIZE    = 23     # Arial Bold 23pt → "OFFICIAL SELECTION" = 244px natural
LABEL_TRACK   = 0      # no extra tracking — natural width already matches sample
YEAR_SIZE     = 20     # Segoe UI 20pt for year
YEAR_TRACK    = 0      # tight, matching sample

BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


# ── FESTIVAL DATA ─────────────────────────────────────────────────
FESTIVALS = [
    # ── Award Winners ─────────────────────────────────────────────
    ("AWARD WINNER",       "Portland Comedy",  "Film Festival",     "2023", "winner-portland-comedy-2023"),
    ("AWARD WINNER",       "Hollywood Best",   "Indie Film Awards", "2026", "winner-hollywood-best-2026"),
    ("AWARD WINNER",       "LA Film &",        "Documentary Award", "2026", "winner-la-doc-2026"),
    ("AWARD WINNER",       "New York Film &",  "Actress Award",     "2026", "winner-ny-actress-2026"),
    ("AWARD WINNER",       "Hollywood Int'l",  "Indie Film Awards", "2026", "winner-hollywood-intl-2026"),
    ("AWARD WINNER",       "Tokyo Film &",     "Screenplay Awards", "2026", "winner-tokyo-2026"),
    ("AWARD WINNER",       "Tamil Int'l",      "Film Festival",     "2025", "winner-canadian-tamil-2025"),
    # ── Finalists ─────────────────────────────────────────────────
    ("FINALIST",           "Portland Comedy",  "Film Festival",     "2023", "finalist-portland-2023"),
    ("FINALIST",           "Houston Comedy",   "Film Festival",     "2023", "finalist-houston-2023"),
    # ── Official Selections ───────────────────────────────────────
    ("OFFICIAL SELECTION", "Los Angeles",      "Short Film Award",  "2026", "sel-la-short-2026"),
    ("OFFICIAL SELECTION", "Canadian Tamil",   "Film Festival",     "2025", "sel-canadian-tamil-a-2025"),
    ("OFFICIAL SELECTION", "Canadian Tamil",   "Film Festival",     "2025", "sel-canadian-tamil-b-2025"),
    ("OFFICIAL SELECTION", "Niagara Canada",   "Film Festival",     "2025", "sel-niagara-2025"),
    ("OFFICIAL SELECTION", "Pickering Canada", "Film Festival",     "2025", "sel-pickering-2025"),
    ("OFFICIAL SELECTION", "Portland Comedy",  "Film Festival",     "2024", "sel-portland-2024"),
    ("OFFICIAL SELECTION", "Pickering Canada", "Film Festival",     "2024", "sel-pickering-2024"),
    ("OFFICIAL SELECTION", "Toronto",          "Film Awards",       "2024", "sel-toronto-2024"),
    ("OFFICIAL SELECTION", "Niagara Canada",   "Film Festival",     "2024", "sel-niagara-2024"),
]


# ── LAUREL GENERATOR ─────────────────────────────────────────────
def make_laurel(label, line1, line2, year, stem, sample_arr, text_mask, out_dir):
    # Start from a clean copy of the sample as an RGBA array
    img_arr = sample_arr.copy()

    # Erase ONLY original text pixels — wreath artwork is untouched
    img_arr[text_mask, :3] = 255    # set R,G,B to white; keep alpha

    img  = Image.fromarray(img_arr)
    draw = ImageDraw.Draw(img)
    W, H = img.size
    cx   = W // 2

    # ── Label ("AWARD WINNER" / "OFFICIAL SELECTION" / "FINALIST") ──
    lf = font(FONT_SANS, LABEL_SIZE)
    lh = th(draw, label, lf)
    draw_tracked(draw, cx, LABEL_CY - lh//2, label, lf, BLACK, LABEL_TRACK)

    # ── Festival name (Arial Bold, auto-sized) ──────────────────────
    sz  = best_name_size(draw, line1, line2, NAME_MAX_W)
    nf  = font(FONT_NAME, sz)
    lh1 = th(draw, line1, nf)
    two = bool(line2)

    # Line spacing: distance from top of line1 to top of line2
    spacing = int(sz * 1.30)

    if two:
        block_h = spacing + lh1
        n1_y    = NAME_BLOCK_CY - block_h//2
        n2_y    = n1_y + spacing
    else:
        n1_y = NAME_BLOCK_CY - lh1//2
        n2_y = None

    draw_centered(draw, cx, n1_y, line1, nf, BLACK)
    if two and line2:
        draw_centered(draw, cx, n2_y, line2, nf, BLACK)

    # ── Year ────────────────────────────────────────────────────────
    yf = font(FONT_SANS, YEAR_SIZE)
    yh = th(draw, year, yf)
    draw_tracked(draw, cx, YEAR_CY - yh//2, year, yf, BLACK, YEAR_TRACK)

    # ── Save ────────────────────────────────────────────────────────
    out_path = os.path.join(out_dir, f'{stem}.png')
    img.convert('RGB').save(out_path, 'PNG')
    print(f'  ✓  {stem}.png   ({sz}pt)')


# ── MAIN ──────────────────────────────────────────────────────────
def main():
    base        = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(base, 'sample laurel.png')
    out_dir     = os.path.join(base, 'laurels')

    if not os.path.isfile(sample_path):
        sys.exit(f'ERROR: {sample_path!r} not found')

    sample     = Image.open(sample_path).convert('RGBA')
    sample_arr = np.array(sample)
    W, H       = sample.size
    print(f'Sample: {W}×{H} px')

    # Compute the text mask once (reused for all laurels)
    print('Analysing text vs wreath pixels…')
    text_mask = build_text_mask(sample_arr)
    n_text    = text_mask.sum()
    print(f'  {n_text} original text pixels identified (wreath untouched)')
    print(f'Output: {out_dir}/')
    print()

    os.makedirs(out_dir, exist_ok=True)

    for item in FESTIVALS:
        label, line1, line2, year, stem = item
        make_laurel(label, line1, line2, year, stem,
                    sample_arr, text_mask, out_dir)

    print(f'\nDone — {len(FESTIVALS)} laurels saved.')


if __name__ == '__main__':
    main()

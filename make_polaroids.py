#!/usr/bin/env python3
"""
make_polaroids.py
Converts photos into Polaroid-style images for the website carousel.

Run from the website directory:
    python3 make_polaroids.py

Output: ./photos/polaroids/  (one PNG per source photo)
"""

from PIL import Image, ImageOps
import os, glob, sys

# ── POLAROID DIMENSIONS ───────────────────────────────────────────
# Inner photo area (4:3 landscape — suits most production stills)
INNER_W = 380
INNER_H = 285
# Borders: classic Polaroid has ~3× border at bottom vs sides
BORDER_LR  = 14
BORDER_TOP = 14
BORDER_BOT = 50
OUTER_W = INNER_W + BORDER_LR * 2
OUTER_H = INNER_H + BORDER_TOP + BORDER_BOT
WHITE   = (255, 255, 255)

# ── FILES TO SKIP ─────────────────────────────────────────────────
SKIP = {
    'test-polaroid.png', 'sample laurel.png', 'font_sans_comparison.png',
    '2023-09-30 - Copy.png',
    # NJ icon variants — branding assets, not photos
    'new jersey icon.png', 'new jersey icon gold.png', 'new jersey icon yellow.png',
    # PNG duplicates where a JPG version exists
    'busty.png', 'cop-stop.png', 'house-of-fun.png',
    # Promo materials (not production stills)
    'thumbnail-2-smaller.png', 'teaser thumbnail.png',
    # Screenshots
    'Screenshot 2023-04-14 091853.png', 'Screenshot 2023-04-14 092030.png',
    'Screenshot 2023-04-15 072253.png', 'Screenshot 2023-04-18 093635.png',
    'Screenshot 2023-04-19 090533.png', 'Screenshot 2023-05-23 081321.png',
    'Screenshot 2023-05-23 081744.png', 'Screenshot 2023-09-25 200220 - Copy.png',
    'Screenshot 2023-11-06 082311.png', 'Screenshot 2023-11-06 082508.png',
    'Screenshot 2023-11-06 082612.png', 'Screenshot 2024-01-03 150619.png',
    'Screenshot 2024-02-09 090028 (1).png', 'Screenshot 2024-02-09 090028.png',
    'Screenshot 2024-06-02 213835.png', 'Screenshot 2024-07-09 065253.png',
    'Screenshot 2025-10-26 161730.png', 'Screenshot 2025-10-26 162346.png',
}


# Per-file crop centre overrides.
# (cx, cy) = fraction of source image to use as crop centre.
#   cx: 0.0=left edge  0.5=centre  1.0=right edge
#   cy: 0.0=top edge   0.5=centre  1.0=bottom edge
CROP_CENTER = {
    '20230127_184811.jpg': (0.28, 0.5),  # actress on far-left was cropped out
    'deflating.png':       (0.5,  0.10), # head cut off — pull crop to top
    'house-of-fun.jpg':    (0.5,  0.42), # people tight — slight upper bias
    'rocco_1.90.1.jpg':    (0.5,  0.32), # show faces not bathroom wall
    '20250426_160237.jpg': (0.58, 0.5),  # Busty on far-right was cropped out
}


def crop_to_ratio(img, target_w, target_h, cx=0.5, cy=0.5):
    """Apply EXIF rotation then crop to target aspect ratio centred at (cx, cy)."""
    img = ImageOps.exif_transpose(img)   # fix sideways/upside-down EXIF
    w, h = img.size
    target_r = target_w / target_h
    current_r = w / h

    if current_r > target_r:
        # Image is wider — crop sides
        new_w = int(h * target_r)
        x0 = max(0, min(int(w * cx - new_w / 2), w - new_w))
        img = img.crop((x0, 0, x0 + new_w, h))
    else:
        # Image is taller — crop top/bottom
        new_h = int(w / target_r)
        y0 = max(0, min(int(h * cy - new_h / 2), h - new_h))
        img = img.crop((0, y0, w, y0 + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def make_polaroid(src_path, dst_path):
    img  = Image.open(src_path).convert('RGB')
    fname = os.path.basename(src_path)
    cx, cy = CROP_CENTER.get(fname, (0.5, 0.5))
    photo = crop_to_ratio(img, INNER_W, INNER_H, cx=cx, cy=cy)

    # White Polaroid frame
    frame = Image.new('RGB', (OUTER_W, OUTER_H), WHITE)
    frame.paste(photo, (BORDER_LR, BORDER_TOP))
    frame.save(dst_path, 'PNG')


def main():
    base      = os.path.dirname(os.path.abspath(__file__))
    photo_dir = os.path.join(base, 'photos')
    out_dir   = os.path.join(photo_dir, 'polaroids')
    os.makedirs(out_dir, exist_ok=True)

    patterns  = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG', '*.png', '*.PNG']
    all_files = []
    for pat in patterns:
        all_files.extend(glob.glob(os.path.join(photo_dir, pat)))

    # Filter, sort, deduplicate
    files = sorted(set(
        f for f in all_files
        if os.path.basename(f) not in SKIP
        and not os.path.basename(f).startswith('polaroid_')  # skip any old outputs
    ))

    print(f'Processing {len(files)} photos → {out_dir}/')
    ok, skip = 0, 0
    for i, src in enumerate(files):
        name = f'polaroid_{i+1:03d}.png'
        dst  = os.path.join(out_dir, name)
        try:
            make_polaroid(src, dst)
            print(f'  ✓  {name}  ← {os.path.basename(src)}')
            ok += 1
        except Exception as e:
            print(f'  ✗  {os.path.basename(src)}: {e}')
            skip += 1

    print(f'\nDone — {ok} polaroids generated, {skip} skipped.')
    print(f'Output: {out_dir}/')


if __name__ == '__main__':
    main()

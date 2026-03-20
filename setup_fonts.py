# setup_fonts.py
# ============================================================
# Downloads the Montserrat font (professional, clean, modern).
# Run ONCE on your Windows PC, then commit fonts/ to GitHub.
#
# If you skip this, the pipeline still works but uses DejaVu Sans
# (looks decent but not as premium as Montserrat).
#
# Run:  python setup_fonts.py
# ============================================================

import io
import sys
import zipfile
from pathlib import Path

import requests

FONTS_DIR = Path("fonts")
FONTS_DIR.mkdir(exist_ok=True)

# Check if already downloaded
bold_ttf = FONTS_DIR / "Montserrat-Bold.ttf"
reg_ttf  = FONTS_DIR / "Montserrat-Regular.ttf"

if bold_ttf.exists() and reg_ttf.exists():
    print("✓ Montserrat fonts already in fonts/ folder — nothing to do.")
    sys.exit(0)

print("Downloading Montserrat from Google Fonts...")

URL = "https://fonts.google.com/download?family=Montserrat"
try:
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        saved = 0
        for name in z.namelist():
            # We want the static (non-variable) Bold and Regular
            if "static" in name and (
                "Montserrat-Bold.ttf" in name or "Montserrat-Regular.ttf" in name
            ):
                filename = Path(name).name
                dest     = FONTS_DIR / filename
                dest.write_bytes(z.read(name))
                print(f"  ✓ {filename}")
                saved += 1

    if saved == 0:
        # Fallback: download individual font files from Google Fonts CDN
        print("  Trying direct CDN download...")
        for fname, url in [
            ("Montserrat-Bold.ttf",
             "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf"),
            ("Montserrat-Regular.ttf",
             "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Regular.ttf"),
        ]:
            r2 = requests.get(url, timeout=60)
            r2.raise_for_status()
            (FONTS_DIR / fname).write_bytes(r2.content)
            print(f"  ✓ {fname}")
            saved += 1

    print(f"\n✅ {saved} font files saved to fonts/")
    print("\nNext steps:")
    print("  git add fonts/")
    print('  git commit -m "Add Montserrat font"')
    print("  git push")

except Exception as exc:
    print(f"\n⚠  Font download failed: {exc}")
    print("The pipeline will use DejaVu Sans (pre-installed on GitHub Actions).")
    print("Videos will still look good — just not as premium as Montserrat.")

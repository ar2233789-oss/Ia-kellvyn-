#!/usr/bin/env python3
"""Align mobile web and Android screenshots using crop-only geometry; never rescale."""
import argparse
import json
from pathlib import Path
from PIL import Image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--candidate-top-px", type=int, required=True)
    p.add_argument("--max-width-rounding-px", type=int, default=1)
    a = p.parse_args()

    web = Image.open(a.reference).convert("RGB")
    native = Image.open(a.candidate).convert("RGB")
    width = min(web.width, native.width)
    if abs(web.width - native.width) > a.max_width_rounding_px:
        p.error(f"width mismatch too large: web={web.size}, Android={native.size}")
    if a.candidate_top_px < 0 or a.candidate_top_px + web.height > native.height:
        p.error(f"Android crop does not fit: web={web.size}, Android={native.size}, top={a.candidate_top_px}")

    # Crop only: remove status/navigation bars and DPR rounding. Never interpolate or resize.
    web_crop = web.crop((0, 0, width, web.height))
    native_crop = native.crop((0, a.candidate_top_px, width, a.candidate_top_px + web.height))
    a.output_dir.mkdir(parents=True, exist_ok=True)
    web_out = a.output_dir / f"{a.name}-reference-aligned.png"
    native_out = a.output_dir / f"{a.name}-candidate-aligned.png"
    web_crop.save(web_out)
    native_crop.save(native_out)
    report = {
        "name": a.name,
        "method": "crop-only; no resize/interpolation",
        "referenceOriginal": list(web.size),
        "candidateOriginal": list(native.size),
        "referenceCrop": [0, 0, width, web.height],
        "candidateCrop": [0, a.candidate_top_px, width, a.candidate_top_px + web.height],
        "alignedSize": [width, web.height],
        "outputReference": str(web_out),
        "outputCandidate": str(native_out),
    }
    (a.output_dir / f"{a.name}-alignment.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

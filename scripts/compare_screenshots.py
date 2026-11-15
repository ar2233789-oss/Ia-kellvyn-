#!/usr/bin/env python3
"""Compare synchronized web/native screenshots and animation frame sequences."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def compare_pair(reference_path: Path, candidate_path: Path, output: Path, name: str,
                 threshold: int = 16) -> dict:
    if not reference_path.is_file() or not candidate_path.is_file():
        raise FileNotFoundError(f"Missing image pair: {reference_path} | {candidate_path}")
    reference = Image.open(reference_path).convert("RGB")
    candidate = Image.open(candidate_path).convert("RGB")
    if reference.size != candidate.size:
        raise ValueError(f"{name}: dimensions differ ({reference.size} vs {candidate.size}); no resizing allowed")
    a = np.asarray(reference, dtype=np.int16)
    b = np.asarray(candidate, dtype=np.int16)
    delta = np.abs(a - b)
    changed = np.any(delta > threshold, axis=2)
    output.mkdir(parents=True, exist_ok=True)
    reference.save(output / f"{name}-reference.png")
    candidate.save(output / f"{name}-candidate.png")
    Image.blend(reference, candidate, 0.5).save(output / f"{name}-overlay.png")
    ImageEnhance.Contrast(ImageChops.difference(reference, candidate)).enhance(4).save(output / f"{name}-diff.png")
    Image.fromarray(np.max(delta, axis=2).astype(np.uint8), mode="L").save(output / f"{name}-heatmap.png")
    return {
        "name": name, "reference": str(reference_path), "candidate": str(candidate_path),
        "dimensions": list(reference.size), "channelThreshold": threshold,
        "changedPixelsPercent": round(float(changed.mean() * 100), 5),
        "meanAbsoluteError": round(float(delta.mean()), 5),
        "rootMeanSquareError": round(float(np.sqrt(np.mean(np.square(delta, dtype=np.float64)))), 5),
        "maxChannelError": int(delta.max()),
    }


def compare_sequence(reference_dir: Path, candidate_dir: Path, output: Path, name: str,
                     threshold: int = 16) -> dict:
    ref = sorted(reference_dir.glob("*.png"))
    got = sorted(candidate_dir.glob("*.png"))
    if not ref or not got:
        raise ValueError(f"{name}: both sequence folders must contain PNG frames")
    if [p.name for p in ref] != [p.name for p in got]:
        raise ValueError(f"{name}: frame names/counts differ; align captures to the same timestamps")
    rows = [compare_pair(a, b, output / "frames", f"{name}-{i:04d}", threshold)
            for i, (a, b) in enumerate(zip(ref, got, strict=True))]
    scores = [r["changedPixelsPercent"] for r in rows]
    return {"name": name, "frameCount": len(rows),
            "meanChangedPixelsPercent": round(float(np.mean(scores)), 5),
            "p95ChangedPixelsPercent": round(float(np.percentile(scores, 95)), 5),
            "maxChangedPixelsPercent": round(float(np.max(scores)), 5), "frames": rows}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path); p.add_argument("--candidate", type=Path)
    p.add_argument("--reference-frames", type=Path); p.add_argument("--candidate-frames", type=Path)
    p.add_argument("--output-dir", type=Path, required=True); p.add_argument("--name", default="comparison")
    p.add_argument("--channel-threshold", type=int, default=16)
    p.add_argument("--fail-over", type=float, default=None,
                   help="Optional changed-pixel limit; omit to produce diagnostic metrics only")
    a = p.parse_args()
    static = a.reference is not None or a.candidate is not None
    sequence = a.reference_frames is not None or a.candidate_frames is not None
    if static == sequence:
        p.error("choose exactly one mode: static pair or paired frame sequences")
    if not 0 <= a.channel_threshold <= 255: p.error("channel threshold must be 0..255")
    try:
        if static:
            if a.reference is None or a.candidate is None: p.error("both static image paths are required")
            result = compare_pair(a.reference, a.candidate, a.output_dir, a.name, a.channel_threshold)
            score = result["changedPixelsPercent"]
        else:
            if a.reference_frames is None or a.candidate_frames is None: p.error("both frame folders are required")
            result = compare_sequence(a.reference_frames, a.candidate_frames, a.output_dir, a.name, a.channel_threshold)
            score = result["maxChangedPixelsPercent"]
    except (FileNotFoundError, ValueError) as e:
        p.error(str(e))
    gate = None if a.fail_over is None else {
        "maxChangedPixelsPercent": a.fail_over, "result": "PASS" if score <= a.fail_over else "FAIL"}
    report = {"status": "compared", "comparison": result, "gate": gate,
              "note": "Metrics are diagnostics. Pixel-perfect requires threshold 0 and zero changed pixels."}
    a.output_dir.mkdir(parents=True, exist_ok=True)
    (a.output_dir / "comparison-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if gate and gate["result"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())

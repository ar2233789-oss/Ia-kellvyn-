#!/usr/bin/env python3
"""Measure live rain motion and lightning flashes from Android screenrecord MP4s."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

SAMPLE_FPS = 5
DECODE_WIDTH = 360
DECODE_HEIGHT = 800


def detect_flash_events(
    brightness: list[float] | np.ndarray,
    fps: float,
    *,
    baseline_seconds: float = 1.0,
    minimum_delta: float = 2.5,
    merge_gap_frames: int = 1,
) -> tuple[list[dict[str, float]], float, float]:
    """Detect brief full-screen light increases while rejecting ordinary rain movement."""
    values = np.asarray(brightness, dtype=np.float32)
    if values.size < 3 or fps <= 0:
        return [], float(np.median(values)) if values.size else 0.0, minimum_delta
    baseline_count = max(3, min(values.size, round(fps * baseline_seconds)))
    baseline_values = values[:baseline_count]
    baseline = float(np.median(baseline_values))
    mad = float(np.median(np.abs(baseline_values - baseline)))
    threshold = max(minimum_delta, 5.0 * 1.4826 * mad)
    active = values > baseline + threshold
    indexes = np.flatnonzero(active)
    if indexes.size == 0:
        return [], baseline, threshold

    groups: list[list[int]] = [[int(indexes[0])]]
    for index_value in indexes[1:]:
        index = int(index_value)
        if index - groups[-1][-1] <= merge_gap_frames + 1:
            groups[-1].append(index)
        else:
            groups.append([index])

    events: list[dict[str, float]] = []
    for group in groups:
        start, end = group[0], group[-1]
        peak = float(np.max(values[group]) - baseline)
        duration = max(1.0 / fps, (end - start + 1) / fps)
        # Lightning wash is global and brief. Reject long layout/panel transitions.
        if duration <= 1.2 and peak >= threshold:
            events.append({
                "startSeconds": round(start / fps, 3),
                "durationSeconds": round(duration, 3),
                "peakBrightnessDelta": round(peak, 3),
            })
    return events, baseline, threshold


def analyze_frames(frames: np.ndarray, sample_fps: int = SAMPLE_FPS) -> dict[str, Any]:
    if frames.ndim != 3 or frames.shape[0] < 3:
        raise ValueError("Video decode produced fewer than three grayscale frames.")
    # Exclude system bars; the main app content and the weather canvas remain in this crop.
    region = frames[:, 55:-75, :]
    means = region.mean(axis=(1, 2))
    events, baseline, threshold = detect_flash_events(means, sample_fps)
    flash_frames = np.zeros(len(frames), dtype=bool)
    for event in events:
        start = int(event["startSeconds"] * sample_fps)
        count = max(1, round(event["durationSeconds"] * sample_fps))
        flash_frames[max(0, start - 1):min(len(frames), start + count + 1)] = True

    deltas = np.abs(region[1:].astype(np.int16) - region[:-1].astype(np.int16))
    usable = ~flash_frames[1:] & ~flash_frames[:-1]
    if usable.any():
        ordinary = deltas[usable]
    else:
        ordinary = deltas
    moving_fraction = (ordinary > 7).mean(axis=(1, 2)) if ordinary.size else np.array([0.0])
    motion_mean = ordinary.mean() if ordinary.size else 0.0

    starts = np.array([event["startSeconds"] for event in events], dtype=np.float32)
    intervals = np.diff(starts) if starts.size >= 2 else np.array([], dtype=np.float32)
    durations = np.array([event["durationSeconds"] for event in events], dtype=np.float32)
    return {
        "sampleFps": sample_fps,
        "decodedFrames": int(frames.shape[0]),
        "sampledDurationSeconds": round((frames.shape[0] - 1) / sample_fps, 3),
        "meanScreenLuminance": round(float(means.mean()), 4),
        "baselineLuminance": round(baseline, 4),
        "flashDetectionThreshold": round(threshold, 4),
        "lightningEventCount": len(events),
        "lightningEvents": events,
        "lightningIntervalSeconds": {
            "values": [round(float(x), 3) for x in intervals],
            "mean": round(float(intervals.mean()), 3) if intervals.size else None,
            "median": round(float(np.median(intervals)), 3) if intervals.size else None,
        },
        "flashDurationSeconds": {
            "mean": round(float(durations.mean()), 3) if durations.size else None,
            "median": round(float(np.median(durations)), 3) if durations.size else None,
        },
        "rainMotion": {
            "meanAdjacentFrameAbsoluteDifference": round(float(motion_mean), 4),
            "meanMovingPixelFraction": round(float(moving_fraction.mean()), 5),
            "p95MovingPixelFraction": round(float(np.percentile(moving_fraction, 95)), 5),
            "validFramePairs": int(usable.sum()) if usable.size else 0,
        },
        "note": "Motion is measured from continuous video frame differences with lightning intervals excluded; randomized particle coordinates are not compared pixel-for-pixel.",
    }


def probe_video(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    if result.returncode:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    parsed = json.loads(result.stdout)
    stream = parsed["streams"][0]
    fmt = parsed.get("format", {})
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "rFrameRate": stream.get("r_frame_rate"),
        "avgFrameRate": stream.get("avg_frame_rate"),
        "frameCount": int(stream["nb_frames"]) if stream.get("nb_frames", "").isdigit() else None,
        "durationSeconds": float(stream.get("duration") or fmt.get("duration") or 0),
    }


def decode_video(path: Path, sample_fps: int = SAMPLE_FPS) -> np.ndarray:
    command = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-vf", f"fps={sample_fps},scale={DECODE_WIDTH}:{DECODE_HEIGHT}:flags=area",
        "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, check=False, timeout=120)
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg decode failed for {path}: {message}")
    frame_bytes = DECODE_WIDTH * DECODE_HEIGHT
    usable_bytes = len(result.stdout) - (len(result.stdout) % frame_bytes)
    if usable_bytes < frame_bytes * 3:
        raise RuntimeError(f"Video {path} decoded to too few frames ({usable_bytes} bytes).")
    return np.frombuffer(result.stdout[:usable_bytes], dtype=np.uint8).reshape(
        -1, DECODE_HEIGHT, DECODE_WIDTH
    )


def analyze_video(path: Path, sample_fps: int = SAMPLE_FPS) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    metadata = probe_video(path)
    frames = decode_video(path, sample_fps)
    measured = analyze_frames(frames, sample_fps)
    return {
        "file": path.as_posix(),
        "fileSizeBytes": path.stat().st_size,
        "video": metadata,
        "measured": measured,
    }


def compare_pair(web: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    wm = web["measured"]
    nm = native["measured"]
    web_interval = wm["lightningIntervalSeconds"]["mean"]
    native_interval = nm["lightningIntervalSeconds"]["mean"]
    web_motion = wm["rainMotion"]["meanMovingPixelFraction"]
    native_motion = nm["rainMotion"]["meanMovingPixelFraction"]

    def ratio(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or a == 0:
            return None
        return round(b / a, 4)

    return {
        "webViewLightningEvents": wm["lightningEventCount"],
        "nativeLightningEvents": nm["lightningEventCount"],
        "nativeToWebLightningIntervalRatio": ratio(web_interval, native_interval),
        "nativeToWebFlashDurationRatio": ratio(
            wm["flashDurationSeconds"]["mean"], nm["flashDurationSeconds"]["mean"]
        ),
        "nativeToWebRainMotionRatio": ratio(web_motion, native_motion),
        "interpretation": "Statistical comparison only: the two recordings are sequential and particle/bolt positions are randomized, so individual frames must not be expected to match.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webview", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-fps", type=int, default=SAMPLE_FPS)
    args = parser.parse_args()
    web = analyze_video(args.webview, args.sample_fps)
    native = analyze_video(args.native, args.sample_fps)
    report = {
        "status": "analyzed",
        "method": "45-second H.264 screenrecord captures from the Android WebView reference and native app on the same PocoF6Virtual AVD; sampled at 5 fps for motion and global flash measurements",
        "webView": web,
        "native": native,
        "comparison": compare_pair(web, native),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

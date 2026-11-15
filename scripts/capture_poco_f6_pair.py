#!/usr/bin/env python3
"""Capture the web reference in Android WebView and native Kellvyn on one PocoF6Virtual AVD."""
from __future__ import annotations

import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path.cwd()
OUT = ROOT / "artifacts" / "poco-f6"
WEB = OUT / "webview"
NATIVE = OUT / "native"
REF_COMPONENT = "com.kellvyn.labreference/.ReferenceActivity"
APP_COMPONENT = "com.kellvyn.assistant/.MainActivity"
REF_PACKAGE = "com.kellvyn.labreference"
APP_PACKAGE = "com.kellvyn.assistant"
SCREEN_W, SCREEN_H, DENSITY = 1220, 2712, 440


def adb(*args: str, timeout: int = 30, check: bool = True) -> str:
    result = subprocess.run(
        ["adb", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(
            "adb " + " ".join(args) + f" failed ({result.returncode}): " + result.stderr.strip()
        )
    return result.stdout.strip()


def capture(name: str, folder: Path) -> Path:
    target = folder / f"{name}.png"
    folder.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True,
        timeout=45,
        check=False,
    )
    if result.returncode or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Could not capture a valid PNG for {name}: {result.stderr!r}")
    target.write_bytes(result.stdout)
    image = Image.open(target)
    if image.size != (SCREEN_W, SCREEN_H):
        raise RuntimeError(f"{name}: expected {SCREEN_W}x{SCREEN_H}, got {image.size}")
    print(f"CAPTURED {folder.name}/{target.name} ({target.stat().st_size} bytes)", flush=True)
    return target


def wait_reference_state(state: str, timeout: int = 75) -> None:
    deadline = time.monotonic() + timeout
    last_log = ""
    while time.monotonic() < deadline:
        last_log = adb(
            "logcat", "-d", "-s", "KellvynWebViewLab:I", timeout=12, check=False
        )
        failed = f"FAILED state={state} "
        ready = f"READY state={state} "
        if failed in last_log:
            line = next((line for line in last_log.splitlines() if failed in line), failed)
            raise RuntimeError("WebView reference could not reach requested state: " + line)
        if ready in last_log:
            return
        time.sleep(1.5)
    (WEB / f"webview-{state}-timeout-log.txt").write_text(last_log, encoding="utf-8")
    raise RuntimeError(f"WebView did not report READY state={state} within {timeout}s")


def capture_reference_state(state: str) -> Path:
    adb("shell", "am", "force-stop", REF_PACKAGE, timeout=30)
    adb("logcat", "-c", timeout=15)
    adb(
        "shell", "am", "start", "-n", REF_COMPONENT,
        "--es", "lab_state", state,
        timeout=45,
    )
    wait_reference_state(state)
    time.sleep(1)
    return capture(f"webview-{state}", WEB)


def screenshot_array(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)


def locate_gold_palette(path: Path) -> tuple[int, int, dict]:
    image = screenshot_array(path)
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    mask = (np.abs(r - 212) <= 24) & (np.abs(g - 175) <= 24) & (np.abs(b - 55) <= 24)
    rows = mask.sum(axis=1)
    # The visible gold palette swatch is a prominent horizontal band inside the
    # right-hand preset card. Ignore status/system areas and choose the strongest row.
    rows[:180] = 0
    rows[-220:] = 0
    y = int(rows.argmax())
    count = int(rows[y])
    if count < 18:
        raise RuntimeError(
            "Could not locate the visible #D4AF37 swatch in the native settings screenshot; "
            "no guessed tap was attempted."
        )
    x = int(image.shape[1] * 0.73)
    return x, y, {
        "method": "screenshot color centroid row + right-hand palette card",
        "target": "#D4AF37",
        "x": x,
        "y": y,
        "goldPixelsAtDetectedRow": count,
        "screenshot": str(path),
        "imageSize": [int(image.shape[1]), int(image.shape[0])],
    }


def verify_native_gold() -> dict:
    raw = adb(
        "shell", "run-as", APP_PACKAGE, "cat", "shared_prefs/kellvyn_native.xml",
        timeout=20,
    )
    (NATIVE / "native-prefs.xml").write_text(raw, encoding="utf-8")
    root = ET.fromstring(raw)
    node = next(
        (item for item in root if item.tag == "int" and item.attrib.get("name") == "accent"),
        None,
    )
    if node is None:
        raise RuntimeError("Native accent preference missing after selecting gold palette.")
    actual = int(node.attrib["value"])
    expected = int.from_bytes(bytes.fromhex("FFD4AF37"), "big", signed=True)
    if actual != expected:
        raise RuntimeError(f"Gold palette did not persist: expected {expected}, actual {actual}")
    return {"expectedSignedArgb": expected, "actualSignedArgb": actual, "passed": True}


def native_ui_tree():
    remote = "/sdcard/kellvyn-layout-ui.xml"
    adb("shell", "uiautomator", "dump", remote, timeout=45)
    raw = adb("shell", "cat", remote, timeout=20)
    return ET.fromstring(raw)


def native_label_point(label: str) -> tuple[int, int] | None:
    root = native_ui_tree()
    parents = {child: node for node in root.iter("node") for child in node}
    for node in root.iter("node"):
        if node.attrib.get("text", "").strip() != label:
            continue
        target = node
        while target is not None and target.attrib.get("clickable") != "true":
            target = parents.get(target)
        if target is None:
            target = node
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",
                             target.attrib.get("bounds", ""))
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def wait_native_label(label: str, timeout: int = 35) -> tuple[int, int]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        point = native_label_point(label)
        if point is not None:
            return point
        time.sleep(1)
    raise RuntimeError(f"Native UI did not expose the expected label: {label}")


def tap_native_label(label: str, timeout: int = 35) -> None:
    x, y = wait_native_label(label, timeout=timeout)
    adb("shell", "input", "tap", str(x), str(y), timeout=20)


def verify_native_effects() -> dict:
    raw = adb(
        "shell", "run-as", APP_PACKAGE, "cat", "shared_prefs/kellvyn_native.xml",
        timeout=20,
    )
    (NATIVE / "native-prefs.xml").write_text(raw, encoding="utf-8")
    root = ET.fromstring(raw)
    node = next(
        (item for item in root if item.tag == "string" and item.attrib.get("name") == "visual_effects"),
        None,
    )
    if node is None:
        raise RuntimeError("Native visual_effects preference missing after selecting lightning.")
    try:
        effects = json.loads(node.attrib["value"])
    except (KeyError, json.JSONDecodeError) as error:
        raise RuntimeError("Native visual_effects preference is not valid JSON.") from error
    if not {"chuva", "raios"}.issubset(set(effects)):
        raise RuntimeError(f"Rain and lightning are not both enabled: {effects}")
    return {"effects": effects, "passed": True}


def capture_native_states() -> dict:
    NATIVE.mkdir(parents=True, exist_ok=True)
    adb("install", "-r", "artifacts/apk/app-debug.apk", timeout=180)
    adb("shell", "am", "force-stop", APP_PACKAGE, timeout=30)
    adb("shell", "am", "start", "-n", APP_COMPONENT, timeout=45)
    time.sleep(12)

    activity = adb("shell", "dumpsys", "activity", "activities", timeout=30)
    if "com.kellvyn.assistant/.MainActivity" not in activity:
        raise RuntimeError("Native MainActivity did not become the foreground activity.")
    crash = adb("logcat", "-d", "-b", "crash", timeout=20)
    if "Process: com.kellvyn.assistant" in crash:
        (NATIVE / "native-crash-buffer.txt").write_text(crash, encoding="utf-8")
        raise RuntimeError("A native app crash was recorded during startup.")

    capture("native-main", NATIVE)

    # Capture the default settings sheet and select the measured gold palette.
    adb("shell", "input", "tap", "1170", "130", timeout=20)
    time.sleep(3)
    settings = capture("native-settings", NATIVE)
    x, y, tap_report = locate_gold_palette(settings)
    (NATIVE / "native-palette-tap.json").write_text(
        json.dumps(tap_report, indent=2) + "\n", encoding="utf-8"
    )
    adb("shell", "input", "tap", str(x), str(y), timeout=20)
    time.sleep(2)
    capture("native-gold-settings", NATIVE)
    gold_pref = verify_native_gold()

    adb("shell", "input", "keyevent", "4", timeout=20)
    time.sleep(2)
    activity = adb("shell", "dumpsys", "activity", "activities", timeout=30)
    if "com.kellvyn.assistant/.MainActivity" not in activity:
        raise RuntimeError("Native app left the foreground after closing Settings.")
    capture("native-gold-main", NATIVE)

    # Turn on lightning while preserving rain, then verify the persisted native state.
    adb("shell", "input", "tap", "1170", "130", timeout=20)
    time.sleep(3)
    wait_native_label("Raios")
    tap_native_label("Raios")
    time.sleep(3)
    wait_native_label("CONFIGURAÇÕES DO KELLVYN")
    capture("native-effects-settings", NATIVE)
    effects_pref = verify_native_effects()
    tap_native_label("Fechar")
    time.sleep(2)
    activity = adb("shell", "dumpsys", "activity", "activities", timeout=30)
    if "com.kellvyn.assistant/.MainActivity" not in activity:
        raise RuntimeError("Native app left the foreground after closing effects Settings.")
    capture("native-effects-main", NATIVE)

    (NATIVE / "native-meminfo.txt").write_text(
        adb("shell", "dumpsys", "meminfo", APP_PACKAGE, timeout=45),
        encoding="utf-8",
    )
    (NATIVE / "native-logcat.txt").write_text(
        adb("logcat", "-d", "-t", "2500", timeout=45),
        encoding="utf-8",
    )
    return {
        "goldPalettePreference": gold_pref,
        "paletteTap": tap_report,
        "rainLightningPreference": effects_pref,
    }

def environment_report() -> dict:
    def prop(name: str) -> str:
        return adb("shell", "getprop", name, timeout=15, check=False)

    return {
        "lab": "PocoF6Virtual",
        "avdName": "PocoF6Virtual",
        "hardwareTemplate": "pixel_7 base template with the original Poco F6 virtual profile overrides",
        "android": {
            "release": prop("ro.build.version.release"),
            "apiLevel": prop("ro.build.version.sdk"),
            "modelProperty": prop("ro.product.model"),
            "manufacturerProperty": prop("ro.product.manufacturer"),
            "buildFingerprint": prop("ro.build.fingerprint"),
            "abi": prop("ro.product.cpu.abi"),
        },
        "display": {
            "wmSize": adb("shell", "wm", "size"),
            "wmDensity": adb("shell", "wm", "density"),
            "expectedPixels": [SCREEN_W, SCREEN_H],
            "expectedDensityDpi": DENSITY,
        },
        "configuredProfile": {
            "ramMb": 8192,
            "cpuCores": 4,
            "gpu": "swiftshader_indirect",
            "systemImage": "android-35;google_apis;x86_64",
        },
    }


def main() -> int:
    WEB.mkdir(parents=True, exist_ok=True)
    NATIVE.mkdir(parents=True, exist_ok=True)

    adb("shell", "wm", "size", f"{SCREEN_W}x{SCREEN_H}")
    adb("shell", "wm", "density", str(DENSITY))
    size = adb("shell", "wm", "size")
    density = adb("shell", "wm", "density")
    if f"{SCREEN_W}x{SCREEN_H}" not in size or str(DENSITY) not in density:
        raise RuntimeError(f"Wrong virtual device viewport: {size}; {density}")

    # Reverse the host Vite port into the AVD. The web page is loaded inside the
    # lab-only WebView APK on the same emulator used for the native screenshots.
    adb("reverse", "tcp:4173", "tcp:4173", timeout=20)
    adb("install", "-r", "artifacts/apk/lab-reference-debug.apk", timeout=180)

    for state in ("main", "settings", "gold-settings", "gold-main", "effects-settings", "effects-main"):
        capture_reference_state(state)

    native_result = capture_native_states()
    env = environment_report()
    report = {
        "status": "captured",
        "comparisonMethod": "web reference rendered in Android WebView and native app rendered on the same PocoF6Virtual AVD",
        "sameDevice": True,
        "sameResolution": [SCREEN_W, SCREEN_H],
        "sameDensityDpi": DENSITY,
        "webViewPackage": REF_PACKAGE,
        "nativePackage": APP_PACKAGE,
        "webViewStates": ["main", "settings", "gold-settings", "gold-main", "effects-settings", "effects-main"],
        "nativeStates": ["main", "settings", "gold-settings", "main after gold palette", "effects-settings", "effects-main"],
        "nativeChecks": native_result,
        "environment": env,
        "note": "This AVD is a Poco F6 virtual profile, not a physical Poco F6/HyperOS device. The WebView reference is test-only and is not part of the Kellvyn release APK.",
    }
    (OUT / "poco-f6-capture-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OUT / "poco-f6-environment.json").write_text(
        json.dumps(env, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("PASS: WebView and native states captured on the same PocoF6Virtual AVD.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "capture-error.json").write_text(
            json.dumps({"status": "failed", "error": str(error)}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"POCO_F6_CAPTURE_ERROR: {error}", flush=True)
        raise

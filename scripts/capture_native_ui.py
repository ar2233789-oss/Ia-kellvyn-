#!/usr/bin/env python3
"""Capture the native Kellvyn UI in an Android emulator with explicit ANR recovery."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "artifacts" / "native"
REMOTE = "/data/local/tmp"
PACKAGE = "com.kellvyn.assistant"
ACTIVITY = f"{PACKAGE}/.MainActivity"
ANR_TITLE = "System UI isn't responding"


def command(args: list[str], *, timeout: int = 90, stdout=None) -> str:
    result = subprocess.run(
        ["adb", *args],
        check=False,
        stdout=subprocess.PIPE if stdout is None else stdout,
        stderr=subprocess.PIPE,
        text=stdout is None,
        timeout=timeout,
    )
    if result.returncode:
        message = result.stderr.strip() if isinstance(result.stderr, str) else ""
        raise RuntimeError(f"adb {' '.join(args)} failed ({result.returncode}): {message}")
    return result.stdout.strip() if isinstance(result.stdout, str) else ""


def dump_ui(name: str = "current-ui") -> Path:
    remote = f"{REMOTE}/{name}.xml"
    local = OUT / f"{name}.xml"
    command(["shell", "uiautomator", "dump", remote], timeout=90)
    command(["pull", remote, str(local)], timeout=45)
    if not local.is_file() or local.stat().st_size == 0:
        raise RuntimeError("UIAutomator returned an empty accessibility tree")
    return local


def tree_nodes(path: Path):
    root = ET.parse(path).getroot()
    parent = {child: node for node in root.iter("node") for child in node}
    return list(root.iter("node")), parent


def find_node(path: Path, label: str, attr: str = "text", exact: bool = True):
    nodes, parents = tree_nodes(path)
    expected = label.strip().casefold()
    for node in nodes:
        value = node.attrib.get(attr, "").strip().casefold()
        if (value == expected if exact else expected in value):
            clickable = node
            while clickable is not None and clickable.attrib.get("clickable") != "true":
                clickable = parents.get(clickable)
            target = clickable if clickable is not None else node
            match = re.fullmatch(
                r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",
                target.attrib.get("bounds", ""),
            )
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                return (x1 + x2) // 2, (y1 + y2) // 2
    return None


def tap_label(path: Path, label: str, attr: str = "text", exact: bool = True) -> bool:
    point = find_node(path, label, attr, exact)
    if point is None:
        return False
    command(["shell", "input", "tap", str(point[0]), str(point[1])], timeout=30)
    return True


def capture(name: str) -> None:
    target = OUT / f"{name}.png"
    with target.open("wb") as stream:
        command(["exec-out", "screencap", "-p"], timeout=45, stdout=stream)
    if not target.is_file() or target.stat().st_size < 10_000:
        raise RuntimeError(f"Screenshot {name} is empty or implausibly small")
    print(f"CAPTURED {target.name} ({target.stat().st_size} bytes)", flush=True)


def recover_system_ui(max_waits: int = 4) -> int:
    waits = 0
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        ui = dump_ui("boot-ui")
        if find_node(ui, ANR_TITLE, exact=True) is not None:
            if waits >= max_waits:
                raise RuntimeError("Android System UI remained unresponsive after repeated Wait actions")
            if not tap_label(ui, "Wait", exact=True):
                raise RuntimeError("System UI ANR dialog appeared without an accessible Wait button")
            waits += 1
            print(f"ANDROID_SYSTEM_UI_ANR: selected Wait ({waits}/{max_waits})", flush=True)
            time.sleep(8)
            continue
        if find_node(ui, "Kellvyn Assistente", exact=True) is not None:
            return waits
        time.sleep(3)
    raise RuntimeError("Kellvyn Assistente did not become visible after launch")


def wait_for_text(label: str, attr: str = "text", timeout: int = 45) -> Path:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = dump_ui("wait-ui")
        if find_node(last, label, attr=attr, exact=True) is not None:
            return last
        if find_node(last, ANR_TITLE, exact=True) is not None:
            if not tap_label(last, "Wait"):
                raise RuntimeError("System UI became unresponsive and offered no Wait button")
            time.sleep(8)
        else:
            time.sleep(2)
    raise RuntimeError(f"Timed out waiting for visible UI label: {label}")


def locate_palette() -> Path:
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        ui = dump_ui("palette-ui")
        point = find_node(ui, "Preto e Dourado")
        if point:
            return ui
        # The settings content is a scroll view; expose the preset row before retrying.
        command(["shell", "input", "swipe", "610", "2180", "610", "1250", "450"], timeout=30)
        time.sleep(1.5)
    raise RuntimeError("The 'Preto e Dourado' preset was not visible in the settings scroll view")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "package": PACKAGE,
        "activity": ACTIVITY,
        "requestedDisplay": {"size": "1220x2712", "densityDpi": 440},
        "anrWaitActions": 0,
        "captures": [],
    }

    command(["shell", "wm", "size", "1220x2712"])
    command(["shell", "wm", "density", "440"])
    command(["install", "-r", "artifacts/apk/app-debug.apk"], timeout=180)
    command(["shell", "am", "start", "-n", ACTIVITY], timeout=45)
    time.sleep(10)

    report["anrWaitActions"] = recover_system_ui()
    capture("native-screen")
    report["captures"].append("native-screen.png")

    ui = wait_for_text("Configurações", attr="content-desc", timeout=30)
    if not tap_label(ui, "Configurações", attr="content-desc"):
        raise RuntimeError("The native settings control was not clickable")
    wait_for_text("CONFIGURAÇÕES DO KELLVYN", timeout=35)
    capture("native-settings")
    report["captures"].append("native-settings.png")

    palette_ui = locate_palette()
    if not tap_label(palette_ui, "Preto e Dourado"):
        raise RuntimeError("Could not tap the gold preset")
    wait_for_text("CONFIGURAÇÕES DO KELLVYN", timeout=35)
    time.sleep(1)
    capture("native-settings-gold")
    report["captures"].append("native-settings-gold.png")

    close_ui = wait_for_text("Fechar", timeout=25)
    if not tap_label(close_ui, "Fechar"):
        raise RuntimeError("Could not close the settings panel after selecting gold")
    wait_for_text("Kellvyn Assistente", timeout=30)
    capture("native-main-gold")
    report["captures"].append("native-main-gold.png")

    (OUT / "native-meminfo.txt").write_text(
        command(["shell", "dumpsys", "meminfo", PACKAGE], timeout=60),
        encoding="utf-8",
    )
    (OUT / "native-logcat.txt").write_text(
        command(["logcat", "-d", "-t", "2000"], timeout=60),
        encoding="utf-8",
    )
    (OUT / "capture-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: all four native screenshots captured; report and diagnostics saved.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        error = {"status": "failed", "error": str(exc)}
        (OUT / "capture-error.json").write_text(
            json.dumps(error, indent=2) + "\n", encoding="utf-8"
        )
        print(f"NATIVE_CAPTURE_ERROR: {exc}", file=sys.stderr, flush=True)
        raise

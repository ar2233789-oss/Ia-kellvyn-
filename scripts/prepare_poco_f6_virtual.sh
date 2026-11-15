#!/usr/bin/env bash
# Exact AVD profile used by the existing Poco F6 virtual laboratory.
set -euo pipefail

SDK_ROOT="\${ANDROID_HOME:-/usr/local/lib/android/sdk}"
SDKMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -name sdkmanager | sort -V | tail -n 1)"
test -n "$SDKMANAGER"

export ANDROID_HOME="$SDK_ROOT"
export ANDROID_SDK_ROOT="$SDK_ROOT"
export ANDROID_AVD_HOME="\${ANDROID_AVD_HOME:-$HOME/.android/avd}"
mkdir -p "$ANDROID_AVD_HOME"
export PATH="$SDK_ROOT/platform-tools:$SDK_ROOT/emulator:$PATH"

set +o pipefail
yes | "$SDKMANAGER" --licenses >/dev/null
set -o pipefail
"$SDKMANAGER" \
  "platforms;android-35" \
  "build-tools;35.0.0" \
  "platform-tools" \
  "emulator" \
  "system-images;android-35;google_apis;x86_64"

AVDMANAGER="$(dirname "$SDKMANAGER")/avdmanager"
if ! "$ANDROID_HOME/emulator/emulator" -list-avds | grep -Fxq "PocoF6Virtual"; then
  echo "no" | "$AVDMANAGER" create avd --force \
    --name PocoF6Virtual \
    --package "system-images;android-35;google_apis;x86_64" \
    --device "pixel_7"
fi

AVD_CONFIG="$ANDROID_AVD_HOME/PocoF6Virtual.avd/config.ini"
test -f "$AVD_CONFIG"

set_avd_prop() {
  local key="$1" value="$2"
  if grep -q "^\${key}=" "$AVD_CONFIG"; then
    sed -i "s|^\${key}=.*|\${key}=\${value}|" "$AVD_CONFIG"
  else
    printf '%s=%s\n' "$key" "$value" >> "$AVD_CONFIG"
  fi
}

set_avd_prop hw.lcd.width 1220
set_avd_prop hw.lcd.height 2712
set_avd_prop hw.lcd.density 440
set_avd_prop hw.ramSize 8192
set_avd_prop hw.cpu.ncore 4
set_avd_prop hw.gpu.enabled yes
set_avd_prop hw.gpu.mode swiftshader_indirect
set_avd_prop disk.dataPartition.size 4096M

python3 - "$AVD_CONFIG" <<'PY'
import json
import sys

config = {}
with open(sys.argv[1], encoding="utf-8") as stream:
    for line in stream:
        if "=" in line:
            key, value = line.rstrip("\n").split("=", 1)
            config[key] = value

expected = {
    "hw.lcd.width": "1220",
    "hw.lcd.height": "2712",
    "hw.lcd.density": "440",
    "hw.ramSize": "8192",
    "hw.cpu.ncore": "4",
    "hw.gpu.enabled": "yes",
    "hw.gpu.mode": "swiftshader_indirect",
    "disk.dataPartition.size": "4096M",
}
mismatches = {}
for key, value in expected.items():
    if config.get(key) != value:
        mismatches[key] = {"expected": value, "actual": config.get(key)}
if mismatches:
    print(json.dumps({"status": "failed", "mismatches": mismatches}, indent=2))
    raise SystemExit(1)

print(json.dumps({
    "status": "passed",
    "avdName": "PocoF6Virtual",
    "hardwareTemplate": "pixel_7 (base template; overridden virtual profile)",
    "androidImage": "android-35;google_apis;x86_64",
    "display": {"widthPx": 1220, "heightPx": 2712, "densityDpi": 440},
    "memoryMb": 8192,
    "cpuCores": 4,
    "gpu": "swiftshader_indirect",
    "dataPartition": "4096M",
}, indent=2))
PY

cp "$AVD_CONFIG" artifacts/poco-f6-avd-config.ini

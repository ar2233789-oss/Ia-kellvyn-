#!/usr/bin/env python3
"""Fail when the web and Android local AI contracts drift apart."""
from __future__ import annotations
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "snapshot/src/components/kellvyn"
ANDROID = ROOT / "snapshot/android/app/src/main/java/com/kellvyn/assistant"


def read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"Required source file is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def one(pattern: str, content: str, label: str, flags: int = 0) -> str:
    match = re.search(pattern, content, flags)
    if not match:
        raise AssertionError(f"Could not find {label}")
    return match.group(1)


def main() -> None:
    web_prompt = read(WEB / "brainPrompt.ts")
    native_brain = read(ANDROID / "LocalBrain.kt")
    native_policy = read(ANDROID / "NativeModelPolicy.java")
    protection = read(ANDROID / "ProtectionPolicy.kt")
    app = read(WEB / "KellvynApp.tsx")
    web_brain = read(WEB / "localBrain.ts")
    gradle = read(ROOT / "snapshot/android/app/build.gradle")

    tick = chr(96)
    web_core = one("const CORE_PROMPT = " + tick + r"([\s\S]*?)" + tick + ";", web_prompt, "web core prompt")
    native_core = one(r'private const val SYSTEM_PROMPT = """([\s\S]*?)"""', native_brain, "native core prompt")
    if web_core != native_core:
        raise AssertionError("The web and Android base system prompts are not byte-for-byte identical")

    web_rules = one("const REINFORCED_RULES = " + tick + r"([\s\S]*?)" + tick + ";", web_prompt, "web reinforced rules")
    native_rules = one(r'private const val REINFORCED_RULES = """([\s\S]*?)"""', protection, "native reinforced rules")
    if web_rules.strip() != textwrap.dedent(native_rules).strip():
        raise AssertionError("The reinforced-protection rules differ between web and Android")

    web_url = one(r'const MODEL_URL =\s*"([^"]+)"', web_brain, "web model URL")
    native_url = one(r'MODEL_URL = "([^"]+)"', native_policy, "native model URL")
    if web_url != native_url:
        raise AssertionError("Web and Android do not use the same pinned model artifact")
    if "EXPECTED_MODEL_BYTES = 2_008_432_640" not in web_brain or "MODEL_BYTES = 2_008_432_640L" not in native_policy:
        raise AssertionError("The expected model byte count differs")

    web_output = int(one(r"maxOutputTokens:\s*(\d+)", web_brain, "web output token limit"))
    native_output = int(one(r"MAX_OUTPUT_TOKENS = (\d+)", native_brain, "native output token limit"))
    if web_output != native_output:
        raise AssertionError(f"Output token limits differ: web={web_output}, native={native_output}")

    web_temp = float(one(r"temperature:\s*([0-9.]+)", web_brain, "web temperature"))
    native_temp = float(one(r"temperature = ([0-9.]+)", native_brain, "native temperature"))
    web_top_p = float(one(r"p:\s*([0-9.]+)", web_brain, "web top-p"))
    native_top_p = float(one(r"topP = ([0-9.]+)", native_brain, "native top-p"))
    web_top_k = int(one(r"k:\s*(\d+)", web_brain, "web top-k"))
    native_top_k = int(one(r"topK = (\d+)", native_brain, "native top-k"))
    if (web_temp, web_top_p, web_top_k) != (native_temp, native_top_p, native_top_k):
        raise AssertionError("Web and Android sampler parameters differ")

    if "maxNumTokens: 4096" not in web_brain or "MAX_CONTEXT_TOKENS = 4096" not in native_brain:
        raise AssertionError("Web and Android context budgets must both be 4096")
    if "litertlm-android:0.18.0" not in gradle or "@litert-lm/core@0.18.0" not in web_brain:
        raise AssertionError("Web and Android LiteRT-LM SDK versions differ")

    if "settings.strongProtection);" not in app or "buildSystemPrompt(strongProtection)" not in web_brain:
        raise AssertionError("The existing web protection toggle is not connected to the model prompt")
    if "ProtectionPolicy.systemInstruction(buildSystemPrompt(), protectionEnabled)" not in native_brain:
        raise AssertionError("The native protection toggle is not connected to the system prompt")
    if native_brain.count('getBoolean("protection", true)') != 2:
        raise AssertionError("Native protection must default to enabled in both conversation paths")

    if "MAX_MEMORIES = 30" not in web_prompt or "MAX_MEMORY_CHARS = 300" not in web_prompt:
        raise AssertionError("Web memory limits changed unexpectedly")
    if "minOf(items.length(), 30)" not in native_brain or "take(300)" not in native_brain:
        raise AssertionError("Native memory limits do not match web")

    print("PASS: base prompt, protection, model revision, SDK, sampler, context, output budget and memory limits match.")


if __name__ == "__main__":
    main()

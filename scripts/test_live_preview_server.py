from __future__ import annotations

import unittest
from pathlib import Path

from live_preview_server import ScreenFeed, build_studio_page

ROOT = Path(__file__).resolve().parents[1]


class LivePreviewStudioTests(unittest.TestCase):
    def test_existing_studio_gets_live_page_and_two_distinct_streams(self) -> None:
        token = "a" * 48
        rendered = build_studio_page(ROOT / "studio" / "index.html", token).decode("utf-8")

        self.assertIn('data-page="live"', rendered)
        self.assertIn('id="page-live"', rendered)
        self.assertIn("/" + token + "/stream/webview", rendered)
        self.assertIn("/" + token + "/stream/native", rendered)
        self.assertIn("Referência WebView", rendered)
        self.assertIn("Android nativo", rendered)
        self.assertIn("PocoF6Virtual", rendered)
        self.assertIn('id="liveOverall"', rendered)

    def test_original_studio_tools_are_preserved(self) -> None:
        rendered = build_studio_page(
            ROOT / "studio" / "index.html",
            "b" * 48,
        ).decode("utf-8")

        self.assertIn('id="page-compare"', rendered)
        self.assertIn('id="page-motion-audit"', rendered)
        self.assertIn('id="page-palette"', rendered)
        self.assertIn('id="page-art"', rendered)
        self.assertIn('id="page-space"', rendered)
        self.assertIn('id="page-motion"', rendered)
        self.assertIn('id="page-logs"', rendered)
        self.assertIn('id="page-report"', rendered)

    def test_new_monitor_is_selected_when_studio_opens(self) -> None:
        rendered = build_live_page = build_studio_page(
            ROOT / "studio" / "index.html",
            "c" * 48,
        ).decode("utf-8")

        self.assertIn('var liveNav = document.querySelector', rendered)
        self.assertIn('if(liveNav) liveNav.click();', rendered)
        self.assertIn('live:"Acompanhamento ao vivo"', rendered)

    def test_feed_starts_disconnected_until_first_adb_frame(self) -> None:
        status = ScreenFeed("emulator-5554", "Nativo").status()

        self.assertFalse(status["connected"])
        self.assertEqual(status["frameNumber"], 0)
        self.assertIsNone(status["frameAgeSeconds"])
        self.assertEqual(status["device"], "emulator-5554")


if __name__ == "__main__":
    unittest.main()

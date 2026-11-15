import unittest

from capture_poco_f6_pair import (
    parse_native_effects_preference,
    parse_webview_raf_metrics,
    parse_native_render_metrics,
)


class NativeEffectsPreferenceTests(unittest.TestCase):
    def test_reads_json_from_android_string_element_text(self):
        raw = (
            '<?xml version="1.0" encoding="utf-8" standalone="yes" ?>'
            '<map><string name="visual_effects">["chuva", "raios"]</string></map>'
        )
        self.assertEqual(
            parse_native_effects_preference(raw),
            ["chuva", "raios"],
        )

    def test_reads_legacy_android_string_set(self):
        raw = (
            '<map><set name="visual_effects">'
            '<string>chuva</string><string>raios</string>'
            '</set></map>'
        )
        self.assertEqual(
            parse_native_effects_preference(raw),
            ["chuva", "raios"],
        )

    def test_rejects_invalid_json_text(self):
        raw = '<map><string name="visual_effects">not-json</string></map>'
        with self.assertRaisesRegex(RuntimeError, "valid JSON"):
            parse_native_effects_preference(raw)

    def test_rejects_non_array_json(self):
        raw = '<map><string name="visual_effects">{"chuva": true}</string></map>'
        with self.assertRaisesRegex(RuntimeError, "JSON string array"):
            parse_native_effects_preference(raw)

    def test_parses_webview_raf_metrics_json(self):
        log = (
            'I/KellvynWebViewLab: WEB RAF_METRIC {"fps":29.5,"timeSeconds":4.2}\n'
            'I/KellvynWebViewLab: WEB RAF_METRIC {"fps":30,"timeSeconds":5.2}\n'
        )
        samples = parse_webview_raf_metrics(log)
        self.assertEqual(len(samples), 2)
        self.assertEqual([item["fps"] for item in samples], [29.5, 30])

    def test_parses_native_render_fps_and_frame_delta(self):
        log = (
            "I/KellvynRainView: renderFps=60 frameDeltaMs=17\n"
            "I/KellvynRainView: renderFps=58 frameDeltaMs=17\n"
        )
        self.assertEqual(
            parse_native_render_metrics(log),
            [{"fps": 60, "frameDeltaMs": 17}, {"fps": 58, "frameDeltaMs": 17}],
        )

    def test_ignores_invalid_or_unrelated_animation_log_lines(self):
        self.assertEqual(
            parse_webview_raf_metrics("RAF_METRIC not-json\nOtherTag: {\"fps\": 30}"),
            [],
        )
        self.assertEqual(parse_native_render_metrics("frame=25 fps=60"), [])

    def test_rejects_missing_preference(self):
        raw = '<map><string name="accent">-7250089</string></map>'
        with self.assertRaisesRegex(RuntimeError, "missing"):
            parse_native_effects_preference(raw)


if __name__ == "__main__":
    unittest.main()

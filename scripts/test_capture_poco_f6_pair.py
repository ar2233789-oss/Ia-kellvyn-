import unittest

from capture_poco_f6_pair import parse_native_effects_preference


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

    def test_rejects_missing_preference(self):
        raw = '<map><string name="accent">-7250089</string></map>'
        with self.assertRaisesRegex(RuntimeError, "missing"):
            parse_native_effects_preference(raw)


if __name__ == "__main__":
    unittest.main()

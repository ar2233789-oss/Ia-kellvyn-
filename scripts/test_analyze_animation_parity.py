import unittest
import numpy as np

from analyze_animation_parity import analyze_frames, detect_flash_events


class AnimationMetricsTests(unittest.TestCase):
    def test_detects_two_broad_lightning_flashes(self):
        values = np.array([20, 20, 20, 20, 30, 40, 32, 20, 20, 20, 20, 31, 39, 20, 20], dtype=float)
        events, baseline, threshold = detect_flash_events(values, fps=5)
        self.assertEqual(len(events), 2)
        self.assertGreater(events[0]["peakBrightnessDelta"], threshold)
        self.assertAlmostEqual(baseline, 20.0)

    def test_ignores_long_luminance_transition(self):
        values = np.array([20] * 5 + [35] * 12 + [20] * 5, dtype=float)
        events, _, _ = detect_flash_events(values, fps=5)
        self.assertEqual(events, [])

    def test_analyzes_real_frame_sequence_shape(self):
        rng = np.random.default_rng(12)
        frames = np.full((20, 800, 360), 18, dtype=np.uint8)
        # Simulate moving rain streaks; frame differences should produce a nonzero motion score.
        for i in range(20):
            x = 30 + i * 5
            frames[i, 100:145, x:x+2] = 220
        result = analyze_frames(frames, sample_fps=5)
        self.assertEqual(result["decodedFrames"], 20)
        self.assertGreater(result["rainMotion"]["meanMovingPixelFraction"], 0)
        self.assertEqual(result["lightningEventCount"], 0)

    def test_requires_at_least_three_frames(self):
        with self.assertRaisesRegex(ValueError, "fewer than three"):
            analyze_frames(np.zeros((2, 800, 360), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()

import importlib.util, tempfile, unittest
from pathlib import Path
import numpy as np
from PIL import Image

FILE = Path(__file__).with_name("compare_screenshots.py")
SPEC = importlib.util.spec_from_file_location("compare_screenshots", FILE)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ref, self.candidate = self.root / "ref.png", self.root / "candidate.png"
        Image.new("RGB", (10, 8), (10, 20, 30)).save(self.ref)

    def tearDown(self): self.temp.cleanup()

    def test_identical_pair_is_zero(self):
        Image.open(self.ref).save(self.candidate)
        r = MOD.compare_pair(self.ref, self.candidate, self.root / "out", "same")
        self.assertEqual(r["changedPixelsPercent"], 0)
        self.assertTrue((self.root / "out" / "same-overlay.png").exists())

    def test_changed_pixels_are_detected(self):
        data = np.zeros((8, 10, 3), dtype=np.uint8); data[:] = (10, 20, 30); data[0, 0] = 255
        Image.fromarray(data).save(self.candidate)
        r = MOD.compare_pair(self.ref, self.candidate, self.root / "out", "changed")
        self.assertGreater(r["changedPixelsPercent"], 0)
        self.assertTrue((self.root / "out" / "changed-heatmap.png").exists())

    def test_dimension_mismatch_is_not_rescaled(self):
        Image.new("RGB", (9, 8)).save(self.candidate)
        with self.assertRaisesRegex(ValueError, "no resizing allowed"):
            MOD.compare_pair(self.ref, self.candidate, self.root / "out", "wrong-size")

    def test_explicit_system_bar_crop_aligns_without_resizing(self):
        Image.new("RGB", (11, 10), (10, 20, 30)).save(self.candidate)
        r = MOD.compare_pair(
            self.ref, self.candidate, self.root / "out", "cropped",
            candidate_crop=(1, 1, 0, 1),
        )
        self.assertEqual(r["changedPixelsPercent"], 0)
        self.assertEqual(r["dimensions"], [10, 8])

    def test_sequence_requires_identical_frame_names(self):
        left, right = self.root / "left", self.root / "right"
        left.mkdir(); right.mkdir()
        Image.open(self.ref).save(left / "000.png")
        Image.open(self.ref).save(right / "001.png")
        with self.assertRaisesRegex(ValueError, "frame names/counts differ"):
            MOD.compare_sequence(left, right, self.root / "out", "frames")


if __name__ == "__main__": unittest.main()

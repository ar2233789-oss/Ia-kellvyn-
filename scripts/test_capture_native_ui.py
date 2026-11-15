import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("capture_native_ui.py")
SPEC = importlib.util.spec_from_file_location("capture_native_ui", SCRIPT)
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


class NativeUiLocatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.xml = Path(self.temp.name) / "ui.xml"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, content: str):
        self.xml.write_text(content, encoding="utf-8")
        return self.xml

    def test_finds_system_ui_anr_wait_button(self):
        path = self.write(
            '<hierarchy><node text="System UI isn\\'t responding" clickable="false" bounds="[10,10][500,80]">'
            '<node text="Wait" clickable="true" bounds="[20,100][490,160]"/>'
            '</node></hierarchy>'
        )
        self.assertEqual(CAPTURE.find_node(path, CAPTURE.ANR_TITLE), None)
        # The Wait node is independently discoverable and clickable.
        self.assertEqual(CAPTURE.find_node(path, "Wait"), (255, 130))

    def test_finds_clickable_parent_for_palette_label(self):
        path = self.write(
            '<hierarchy><node text="" clickable="true" bounds="[100,200][900,320]">'
            '<node text="Preto e Dourado" clickable="false" bounds="[260,220][720,300]"/>'
            '</node></hierarchy>'
        )
        self.assertEqual(CAPTURE.find_node(path, "Preto e Dourado"), (500, 260))

    def test_supports_accessibility_content_description(self):
        path = self.write(
            '<hierarchy><node content-desc="Configurações" clickable="true" bounds="[1100,80][1200,180]"/></hierarchy>'
        )
        self.assertEqual(CAPTURE.find_node(path, "Configurações", attr="content-desc"), (1150, 130))

    def test_missing_label_returns_none_instead_of_crashing(self):
        path = self.write('<hierarchy><node text="Kellvyn Assistente" bounds="[0,0][100,100]"/></hierarchy>')
        self.assertIsNone(CAPTURE.find_node(path, "Preto e Dourado"))


if __name__ == "__main__":
    unittest.main()
